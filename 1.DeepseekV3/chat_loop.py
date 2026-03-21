import os
import sys
import json
import time
import requests

# ========== 清除代理环境变量，防止请求被转发到错误端口 ==========
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

# ========== 获取脚本所在目录 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ROUND_FILE = os.path.join(BASE_DIR, "last_round.txt")  # 用于保存上一次的轮次

# ========== 加载配置文件 ==========
role_name = "默认角色"
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
            role_name = config.get("character_name", role_name)
        print(f"✅ 已加载角色配置：{role_name}")
    except Exception as e:
        print(f"⚠️ 读取配置文件失败，将使用默认角色名。错误：{e}")
else:
    print("ℹ️ 未找到 config.json，将使用默认角色名。")
    print("   你可以创建 config.json 文件自定义角色名，例如：")
    print('   {"character_name": "千机300B"}')

# ========== 读取上次的轮次 ==========
def load_round():
    if os.path.exists(ROUND_FILE):
        try:
            with open(ROUND_FILE, 'r') as f:
                return int(f.read().strip())
        except:
            return 0
    return 0

def save_round(round_num):
    try:
        with open(ROUND_FILE, 'w') as f:
            f.write(str(round_num))
    except:
        pass

# ========== 服务地址配置 ==========
os.environ["RAG_PORT"] = "8003"
os.environ["DEEPSEEK_PORT"] = "8004"
RAG_HOST = os.getenv("RAG_HOST", "127.0.0.1")
RAG_PORT = os.getenv("RAG_PORT", "8003")
DEEPSEEK_HOST = os.getenv("DEEPSEEK_HOST", "127.0.0.1")
DEEPSEEK_PORT = os.getenv("DEEPSEEK_PORT", "8004")

if RAG_PORT != "8003":
    print(f"⚠️ 当前 RAG_PORT 环境变量设置为 {RAG_PORT}，这可能导致连接失败。如需恢复默认，请在命令行执行: set RAG_PORT=")
if DEEPSEEK_PORT != "8004":
    print(f"⚠️ 当前 DEEPSEEK_PORT 环境变量设置为 {DEEPSEEK_PORT}，这可能导致连接失败。如需恢复默认，请在命令行执行: set DEEPSEEK_PORT=")

RAG_URL = f"http://{RAG_HOST}:{RAG_PORT}"
DEEPSEEK_URL = f"http://{DEEPSEEK_HOST}:{DEEPSEEK_PORT}"

# 调试：打印实际使用的 RAG 地址
print("DEBUG: RAG_URL =", RAG_URL)

print("=" * 60)
print("客户端配置：")
print(f"RAG 服务地址: {RAG_URL}")
print(f"DeepSeek 服务地址: {DEEPSEEK_URL}")
print(f"当前角色: {role_name}")
print("=" * 60)

def check_service(url, service_name, retries=3, delay=2):
    for i in range(retries):
        try:
            # 在请求中明确不使用代理
            resp = requests.get(f"{url}/health", timeout=5, proxies={"http": None, "https": None})
            if resp.status_code == 200:
                print(f"✅ {service_name} 服务正常")
                return True
            else:
                print(f"⚠️ {service_name} 服务返回异常状态码: {resp.status_code}")
        except requests.exceptions.ConnectionError:
            if i < retries - 1:
                print(f"⏳ {service_name} 服务尚未就绪，{delay}秒后重试 ({i+1}/{retries})...")
                time.sleep(delay)
            else:
                print(f"❌ 无法连接到 {service_name} 服务，请确保服务已启动")
        except Exception as e:
            print(f"❌ 检查 {service_name} 服务时发生错误: {e}")
            break
    return False

def main():
    print("\n正在检查服务状态...")
    rag_ok = check_service(RAG_URL, "RAG")
    deepseek_ok = check_service(DEEPSEEK_URL, "DeepSeek")
    if not rag_ok or not deepseek_ok:
        print("\n❌ 服务未就绪，无法开始对话。")
        print("请确保已运行 start.bat 启动所有服务。")
        input("按回车键退出...")
        return

    conv_id = None
    round_num = load_round()  # 从文件加载上次的轮次
    print(f"从上次对话继续，当前轮次: {round_num}")

    print("\n开始多轮对话（输入 'exit' 退出）\n")
    while True:
        user_input = input("你: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            break

        if len(user_input) > 500:
            print("⚠️ 输入过长，已截断至500字符")
            user_input = user_input[:500]

        # RAG 检索
        rag_context = ""
        try:
            rag_resp = requests.post(
                f"{RAG_URL}/search_hybrid",
                json={"query": user_input, "top_k": 10, "current_round": round_num},
                timeout=10,
                proxies={"http": None, "https": None}
            )
            rag_resp.raise_for_status()
            rag_data = rag_resp.json()
            rag_context = "\n".join([r["text"] for r in rag_data["results"]])
            print("\n🔍 检索到的上下文片段:")
            print(rag_context if rag_context else "(空)")
            print("-" * 50)
        except requests.exceptions.Timeout:
            print("⏱️ RAG 检索超时，将跳过本次检索")
        except requests.exceptions.ConnectionError:
            print("🔌 无法连接到 RAG 服务，请检查服务是否运行")
        except Exception as e:
            print(f"⚠️ RAG 检索失败: {e}")

        # 调用 DeepSeek
        payload = {
            "messages": [{"role": "user", "content": user_input}],
            "rag_context": rag_context,
            "temperature": 0.7,
            "save_conversation": True,
            "conversation_id": conv_id,
            "auto_add_to_rag": True,
            "current_round": round_num
        }
        try:
            gen_resp = requests.post(
                f"{DEEPSEEK_URL}/generate",
                json=payload,
                timeout=30,
                proxies={"http": None, "https": None}
            )
            gen_resp.raise_for_status()
            data = gen_resp.json()
            reply = data["reply"]
            conv_id = data["conversation_id"]
            print(f"{role_name}: {reply}\n")
            # 成功生成回复后，轮次加1，并保存
            round_num += 1
            save_round(round_num)
        except requests.exceptions.Timeout:
            print("⏱️ DeepSeek 生成超时，请稍后重试")
        except requests.exceptions.ConnectionError:
            print("🔌 无法连接到 DeepSeek 服务，请检查服务是否运行")
        except Exception as e:
            print(f"⚠️ 生成失败: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 对话已结束")
    except Exception as e:
        print(f"\n❌ 发生意外错误: {e}")
        input("按回车键退出...")