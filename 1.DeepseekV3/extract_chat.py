import json
import sys
from datetime import datetime

def extract_messages_from_jsonl(input_file, output_file):
    """
    从SillyTavern导出的JSONL文件中提取纯文本对话
    格式：每行一个JSON对象，包含"name"（发言人）和"mes"（消息内容）
    """
    with open(input_file, 'r', encoding='utf-8') as fin, \
         open(output_file, 'w', encoding='utf-8') as fout:
        
        for line_num, line in enumerate(fin, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                print(f"警告：第{line_num}行不是有效的JSON，已跳过")
                continue
            
            # 提取发言人姓名和消息内容
            name = msg.get('name', 'Unknown')
            content = msg.get('mes', '')
            if not content:
                continue
            
            # 写入纯文本： 姓名: 内容
            fout.write(f"{name}: {content}\n")
    
    print(f"提取完成，结果已保存至 {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python extract_chat.py <输入的JSONL文件> [输出的文本文件]")
        sys.exit(1)
    
    input_path = sys.argv[1]
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        # 默认输出为输入文件名 + .txt
        output_path = input_path.rsplit('.', 1)[0] + '.txt'
    
    extract_messages_from_jsonl(input_path, output_path)