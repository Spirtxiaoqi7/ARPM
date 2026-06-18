# LOCOMO full ARPM result

Evaluation size: 1,986 QA records.

This page reports one complete LOCOMO run using the full ARPM method: BGE-M3 embedding, dual-route retrieval, RRF fusion, and BM25 keyword retrieval.

Metric convention: F1 is reported on answerable questions only, because unanswerable questions require a separate abstention / IDK-style evaluation. Other retrieval, EM, and white-box metrics follow the validated full-run figure and chart.

Main metrics: Hit@5 60.93%, Hit@10 71.75%, MRR 48.24%, EM 12.64%, answerable-question F1 41.05%.

Unanswerable-question handling: blank responses are normalized as IDK-like abstentions when evaluating abstention behavior. The validated unanswerable-question IDK hit rate is 93.95%.

White-box metrics: evidence entered prompt rate 83.28%, all evidence entered prompt rate 71.80%, semantic analysis hit rate 46.88%, answer-evidence binding rate 39.87%, temporal reasoning correctness 52.96%, white-box reasonable abstention rate 46.64%, answerable-question abstention rate 22.14%.

![LOCOMO white-box metrics](./fig_whitebox_analysis_metrics.svg)
