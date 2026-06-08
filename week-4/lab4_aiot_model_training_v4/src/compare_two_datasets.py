from __future__ import annotations

import pandas as pd

from config import OUTPUTS, DATASET_CONFIGS


def main():
    comp = pd.read_csv(OUTPUTS / 'model_comparison.csv')
    lines = []
    lines.append('# So sánh hành vi model trên hai dataset\n\n')
    lines.append('Bảng `model_comparison.csv` cho biết model tốt nhất theo validation MAE và kết quả trên test set.\n\n')
    for _, row in comp.iterrows():
        dataset = row['dataset']
        cfg = DATASET_CONFIGS[dataset]
        lines.append(f"## {cfg['display_name']}\n\n")
        lines.append(f"- Target: `{cfg['target']}`; horizon: {cfg['horizon_minutes']} phút.\n")
        lines.append(f"- Best model by validation MAE: `{row['best_model_by_val_mae']}`.\n")
        lines.append(f"- Test MAE: {row['best_model_test_mae']:.4f}; Last Value MAE: {row['last_value_test_mae']:.4f}.\n")
        lines.append(f"- Improvement vs Last Value: {row['mae_improvement_vs_last_value_percent']:.2f}%.\n")
        lines.append('\nCâu hỏi: Nếu cải thiện không nhiều, có phải model AI vô dụng không? Hay Last Value là baseline rất mạnh vì chuỗi biến thiên chậm?\n\n')
    lines.append('## Câu hỏi tổng hợp\n\n')
    lines.append('1. Dataset nào Last Value baseline đã mạnh? Vì sao?\n')
    lines.append('2. Dataset nào model phi tuyến cải thiện rõ hơn?\n')
    lines.append('3. Nếu model phức tạp hơn nhưng test MAE không giảm, nên chọn model nào khi triển khai thật?\n')
    lines.append('4. Kết quả này nói gì về việc không nên đánh giá AI chỉ bằng cảm giác?\n')
    out = OUTPUTS / 'two_dataset_comparison_notes.md'
    out.write_text(''.join(lines), encoding='utf-8')
    print(out.read_text(encoding='utf-8'))


if __name__ == '__main__':
    main()
