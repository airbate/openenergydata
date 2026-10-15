# oed 基准排行榜

切分: 前 80% 训练 / 后 20% 测试（时间顺序）。指标: MAE/RMSE（通道单位）, MAPE%。

| 任务 | 数据集 | 站点 | 通道/电器 | 基线 | MAE | RMSE | MAPE% | SAE% |
|---|---|---|---|---|---|---|---|---|
| forecast | redd-oed | house_1 | ch01 | naive | 885.0 | 1026.231 | 44.23 |  |
| forecast | redd-oed | house_1 | ch01 | daily_profile | 450.0 | 519.543 | 20.35 |  |
| forecast | redd-oed | house_1 | ch01 | seasonal_lag_24h | 885.0 | 1026.231 | 44.23 |  |
| nilm | redd-oed | house_1 | electric oven | daily_profile | 214.391 | 2418.82 | 26.33 | 36.5 |
