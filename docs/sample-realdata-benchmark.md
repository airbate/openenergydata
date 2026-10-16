# oed 基准排行榜

切分: 前 80% 训练 / 后 20% 测试（时间顺序）。指标: MAE/RMSE（通道单位）, MAPE%。

| 任务 | 数据集 | 站点 | 通道/电器 | 基线 | MAE | RMSE | MAPE% | SAE% |
|---|---|---|---|---|---|---|---|---|
| forecast | redd-pvaug-oed | redd_house1 | mains | naive | 104.827 | 287.256 | 32.64 |  |
| forecast | redd-pvaug-oed | redd_house1 | mains | daily_profile | 139.424 | 282.511 | 492.78 |  |
| forecast | redd-pvaug-oed | redd_house1 | mains | seasonal_lag_24h | 234.784 | 623.418 | 1004.32 |  |
| nilm | redd-pvaug-oed | redd_house1 | aggregate_power_with_injection | daily_profile | 121.051 | 269.393 | 273.09 | 24.92 |
| nilm | redd-pvaug-oed | redd_house1 | microwave oven | daily_profile | 21.773 | 153.596 | 157.7 | 47.52 |
| nilm | redd-pvaug-oed | redd_house1 | fridge | daily_profile | 68.619 | 100.384 | 332.02 | 46.49 |
| nilm | redd-pvaug-oed | redd_house1 | dish washer | daily_profile | 28.685 | 149.785 | 155.84 | 82.19 |
| nilm | redd-pvaug-oed | redd_house1 | washing machine | daily_profile | 46.716 | 153.941 | 4676.96 | 105872.78 |
| nilm | redd-pvaug-oed | redd_house1 | PV inverter | daily_profile | 25.524 | 54.666 | 357.8 | 28.0 |
| nilm | redd-pvaug-oed | redd_house1 | micro_inv | daily_profile | 0.159 | 0.31 | 17.73 | 17.74 |
| nilm | redd-pvaug-oed | redd_house1 | micro_inverter_normalized | daily_profile | 0.013 | 0.027 | 357.8 | 28.0 |
