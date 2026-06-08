from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

from config import DATASET_CONFIGS, MODELS, OUTPUTS, FIGURES
from feature_engineering import make_lstm_arrays
from utils import print_header, regression_metrics

try:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset
except Exception as exc:  # pragma: no cover - only used when torch is unavailable.
    torch = None
    nn = None
    DataLoader = None
    TensorDataset = None
    TORCH_IMPORT_ERROR = exc
else:
    TORCH_IMPORT_ERROR = None


class LSTMRegressor(nn.Module):
    def __init__(self, n_features: int, hidden_size: int = 24, num_layers: int = 1):
        super().__init__()
        self.lstm = nn.LSTM(input_size=n_features, hidden_size=hidden_size, num_layers=num_layers, batch_first=True)
        self.head = nn.Sequential(nn.Linear(hidden_size, 16), nn.ReLU(), nn.Linear(16, 1))

    def forward(self, x):
        out, _ = self.lstm(x)
        last = out[:, -1, :]
        return self.head(last).squeeze(-1)


def split_arrays(X, y, ts, train_ratio=0.60, val_ratio=0.20):
    n = len(X)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    return (
        X[:train_end], y[:train_end], ts[:train_end],
        X[train_end:val_end], y[train_end:val_end], ts[train_end:val_end],
        X[val_end:], y[val_end:], ts[val_end:],
    )


def scale_sequence_data(X_train, X_val, X_test, y_train, y_val, y_test):
    n_features = X_train.shape[-1]
    x_scaler = StandardScaler()
    X_train_2d = X_train.reshape(-1, n_features)
    x_scaler.fit(X_train_2d)
    def tx(x):
        return x_scaler.transform(x.reshape(-1, n_features)).reshape(x.shape).astype(np.float32)
    y_scaler = StandardScaler()
    y_scaler.fit(y_train.reshape(-1, 1))
    return (
        tx(X_train), tx(X_val), tx(X_test),
        y_scaler.transform(y_train.reshape(-1, 1)).ravel().astype(np.float32),
        y_scaler.transform(y_val.reshape(-1, 1)).ravel().astype(np.float32),
        y_scaler.transform(y_test.reshape(-1, 1)).ravel().astype(np.float32),
        x_scaler, y_scaler,
    )


def train_one_dataset(dataset_key: str, config: dict, epochs: int, hidden_size: int, batch_size: int, max_sequences: int):
    print_header(f'Training optional LSTM for {dataset_key}')
    df = pd.read_csv(config['processed_file'])
    X, y, ts, feature_cols = make_lstm_arrays(
        df,
        timestamp_col=config['timestamp'],
        target_col=config['target'],
        horizon_steps=config['horizon_steps'],
        sequence_length=config['sequence_length'],
    )
    if max_sequences and len(X) > max_sequences:
        # Keep a chronological subset for quick classroom CPU experiments.
        X = X[-max_sequences:]
        y = y[-max_sequences:]
        ts = ts[-max_sequences:]
    X_train, y_train, ts_train, X_val, y_val, ts_val, X_test, y_test, ts_test = split_arrays(X, y, ts)
    X_train_s, X_val_s, X_test_s, y_train_s, y_val_s, y_test_s, x_scaler, y_scaler = scale_sequence_data(X_train, X_val, X_test, y_train, y_val, y_test)

    torch.set_num_threads(1)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = LSTMRegressor(n_features=X_train_s.shape[-1], hidden_size=hidden_size).to(device)
    optim = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss()
    train_loader = DataLoader(TensorDataset(torch.tensor(X_train_s), torch.tensor(y_train_s)), batch_size=batch_size, shuffle=False)
    val_x = torch.tensor(X_val_s, device=device)
    val_y = torch.tensor(y_val_s, device=device)

    history = []
    best_val = float('inf')
    best_state = None
    patience = 3
    stale = 0
    for epoch in range(1, epochs + 1):
        model.train()
        losses = []
        for xb, yb in train_loader:
            xb = xb.to(device)
            yb = yb.to(device)
            optim.zero_grad()
            pred = model(xb)
            loss = loss_fn(pred, yb)
            loss.backward()
            optim.step()
            losses.append(float(loss.detach().cpu().item()))
        model.eval()
        with torch.no_grad():
            val_pred = model(val_x)
            val_loss = float(loss_fn(val_pred, val_y).detach().cpu().item())
        train_loss = float(np.mean(losses))
        history.append({'epoch': epoch, 'train_loss': train_loss, 'val_loss': val_loss})
        print(f'{dataset_key} epoch {epoch:02d}: train_loss={train_loss:.5f} val_loss={val_loss:.5f}')
        if val_loss < best_val:
            best_val = val_loss
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= patience:
                print(f'Early stopping at epoch {epoch}')
                break
    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        test_pred_scaled = model(torch.tensor(X_test_s, device=device)).detach().cpu().numpy()
    test_pred = y_scaler.inverse_transform(test_pred_scaled.reshape(-1, 1)).ravel()
    metrics = regression_metrics(y_test, test_pred)

    # Save model package.
    torch.save({
        'model_state_dict': model.state_dict(),
        'n_features': X_train_s.shape[-1],
        'hidden_size': hidden_size,
        'feature_cols': feature_cols,
        'target': config['target'],
        'timestamp_col': config['timestamp'],
        'sequence_length': config['sequence_length'],
        'horizon_steps': config['horizon_steps'],
        'x_scaler_mean': x_scaler.mean_,
        'x_scaler_scale': x_scaler.scale_,
        'y_scaler_mean': y_scaler.mean_,
        'y_scaler_scale': y_scaler.scale_,
    }, MODELS / f'{dataset_key}_lstm.pt')

    pred_df = pd.DataFrame({config['timestamp']: ts_test, 'actual': y_test, 'pred_LSTM': test_pred, 'error': test_pred - y_test})
    pred_df.to_csv(OUTPUTS / f'lstm_predictions_{dataset_key}.csv', index=False)
    pd.DataFrame(history).to_csv(OUTPUTS / f'lstm_history_{dataset_key}.csv', index=False)

    # Loss chart.
    hist = pd.DataFrame(history)
    plt.figure(figsize=(7, 4))
    plt.plot(hist['epoch'], hist['train_loss'], label='train loss')
    plt.plot(hist['epoch'], hist['val_loss'], label='validation loss')
    plt.xlabel('epoch')
    plt.ylabel('MSE loss, scaled target')
    plt.title(f'LSTM training curve - {dataset_key}')
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / f'lstm_loss_{dataset_key}.png', dpi=160)
    plt.close()

    return {'dataset': dataset_key, 'model': 'LSTM_optional', 'split': 'test', **metrics, 'epochs_ran': len(history), 'hidden_size': hidden_size, 'sequence_length': config['sequence_length']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=6)
    parser.add_argument('--hidden-size', type=int, default=24)
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--max-sequences', type=int, default=1200, help='Limit number of chronological sequences for quick CPU runs; set 0 for full data.')
    parser.add_argument('--datasets', type=str, default='appliances', help='Comma-separated dataset keys. Use appliances,co2 to run both.')
    args = parser.parse_args()

    if torch is None:
        msg = f'PyTorch is not installed; LSTM extension skipped. Install with: pip install -r requirements_lstm.txt. Error: {TORCH_IMPORT_ERROR}'
        print(msg)
        (OUTPUTS / 'lstm_skipped.txt').write_text(msg, encoding='utf-8')
        return

    rows = []
    selected = [x.strip() for x in args.datasets.split(',') if x.strip()]
    for dataset_key in selected:
        if dataset_key not in DATASET_CONFIGS:
            raise ValueError(f'Unknown dataset key: {dataset_key}')
        config = DATASET_CONFIGS[dataset_key]
        rows.append(train_one_dataset(dataset_key, config, epochs=args.epochs, hidden_size=args.hidden_size, batch_size=args.batch_size, max_sequences=args.max_sequences))
    pd.DataFrame(rows).to_csv(OUTPUTS / 'lstm_metrics.csv', index=False)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == '__main__':
    main()
