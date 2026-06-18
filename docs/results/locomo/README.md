# LOCOMO full ARPM result

Evaluation size: 1,986 QA records.

For comparability with standard LOCOMO reports, EM and F1 are reported on answerable questions only. The run contains 1,542 answerable questions and 444 unanswerable questions.

Standard answerable-question metrics: Hit@5 63.23%, Hit@10 73.80%, MRR 50.89%, EM 16.21%, F1 41.05%.

Unanswerable-question handling: blank responses are normalized as IDK-like abstentions. The unanswerable-question IDK hit rate is 93.92%.

White-box metrics: evidence entered prompt rate 83.28%, all evidence entered prompt rate 71.80%, semantic analysis hit rate 46.88%, answer-evidence binding rate 39.87%, temporal reasoning correctness 52.96%, white-box reasonable abstention rate 46.64%, answerable-question abstention rate 20.75%.

![LOCOMO white-box metrics](./fig_whitebox_analysis_metrics.svg)
