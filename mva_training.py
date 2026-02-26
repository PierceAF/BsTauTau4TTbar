#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import argparse
import warnings


warnings.filterwarnings("ignore")
import numpy as np

# English comment: Hotfix for ROOT 6.26/NumPy 1.24+ compatibility.
# We do this quietly to avoid the FutureWarning.
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    if not hasattr(np, 'object'):
        np.object = object

        

try:
    import pandas as pd
except ValueError:
    if 'pandas' in sys.modules: del sys.modules['pandas']
    import pandas as pd

import ROOT
import xgboost as xgb
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_curve, auc
import matplotlib.pyplot as plt
from xgboost import plot_importance

warnings.filterwarnings("ignore", category=UserWarning)

# English comment: Import the configuration from features.py
try:
    from features import FEATURES_DICT, CUT_DICT, BASE_VARS
except ImportError:
    print("Error: features.py not found.")
    sys.exit(1)

def load_data(input_file, tree_name, mode, sample_type):
    """Loads and filters data by mode and signal/bkg flag."""
    f = ROOT.TFile.Open(input_file)
    if not f or f.IsZombie():
        return pd.DataFrame()
        
    tree = f.Get(tree_name)
    features = FEATURES_DICT[mode]
    base_cut = CUT_DICT[mode]
    target_var = f"Bs{mode}_is_true_signal" if not hasattr(tree, 'is_true_signal') else 'is_true_signal'
    
    extra_cut = f"{target_var} == 1" if sample_type == "Signal" else f"{target_var} == 0"
    full_selection = f"({base_cut}) && ({extra_cut})"
    
    weight_vars = ['L1PreFiringWeight_Nom', 'genWeight', 'puWeight']
    all_needed = list(set(features + weight_vars + [target_var]))
    data_dict = {var: [] for var in all_needed}
    
    print(f"    Target: {target_var} | Sample: {sample_type} | Cut: {full_selection}")
    
    formula = ROOT.TTreeFormula("selection", full_selection, tree)
    for i in range(tree.GetEntries()):
        tree.GetEntry(i)
        if not formula.EvalInstance(): continue
        for var in all_needed:
            val = getattr(tree, var)
            if hasattr(val, '__getitem__') and not isinstance(val, (str, bytes)):
                try: val = val[0]
                except: val = -999.0
            data_dict[var].append(float(val))
    
    f.Close()
    df = pd.DataFrame(data_dict)
    if not df.empty:
        df['target'] = df[target_var]
        df['event_weight'] = df['L1PreFiringWeight_Nom'] * df['genWeight'] * df['puWeight']


    print(f"    Sample: {sample_type:10} | Target: {target_var:30} | Loaded: {len(df)}")

    return df

def run_training_cv(mode, sig_file, bkg_file, n_folds=5):
    out_dir = f"mva/mva_results_{mode}_CV"
    if not os.path.exists(out_dir): os.makedirs(out_dir)

    print(f"\n>>> Loading ROOT files for mode: {mode}")
    df_sig = load_data(sig_file, "tree", mode, "Signal")
    df_bkg = load_data(bkg_file, "tree", mode, "Background")
    
    print(f"\n>>> Total Statistics after cuts:")
    print(f"    Signal:     {len(df_sig)} events")
    print(f"    Background: {len(df_bkg)} events")
    print(f"    Total:      {len(df_sig) + len(df_bkg)} events")
    
    # 1. Load Data
    df = pd.concat([df_sig, df_bkg], ignore_index=True)

    features = FEATURES_DICT[mode]
    X = df[features]
    y = df['target']
    w = df['event_weight']

    # 2. Setup K-Fold for stability check
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
    tprs = []
    aucs = []
    mean_fpr = np.linspace(0, 1, 100)
    fig_roc, ax_roc = plt.subplots(figsize=(7, 7))

    print(f"\n>>> Starting {n_folds}-Fold Cross-Validation for validation...")
    for i, (train_idx, test_idx) in enumerate(skf.split(X, y)):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        w_train, w_test = w.iloc[train_idx], w.iloc[test_idx]

        n_sig_tr, n_bkg_tr = np.sum(y_train == 1), np.sum(y_train == 0)
        n_sig_te, n_bkg_te = np.sum(y_test == 1), np.sum(y_test == 0)
        spw = np.sum(w_train[y_train == 0]) / np.sum(w_train[y_train == 1])

        print(f"\n--- Fold {i} Statistics ---")
        print(f"    [Train] Signal: {n_sig_tr}, Background: {n_bkg_tr}")
        print(f"    [Test]  Signal: {n_sig_te}, Background: {n_bkg_te}")
        print(f"    [Config] scale_pos_weight: {spw:.3f}")
        
        spw = np.sum(w_train[y_train == 0]) / np.sum(w_train[y_train == 1])
        model = xgb.XGBClassifier(
            max_depth=5, learning_rate=0.1, n_estimators=500,
            subsample=0.8, colsample_bytree=0.8,
            scale_pos_weight=spw, n_jobs=-1, random_state=42,
            early_stopping_rounds=20, eval_metric=['logloss', 'auc']
        )
        model.fit(X_train, y_train, sample_weight=w_train,
                  eval_set=[(X_test, y_test)], sample_weight_eval_set=[w_test], verbose=False)

        y_prob = model.predict_proba(X_test)[:, 1]
        fpr, tpr, _ = roc_curve(y_test, y_prob, sample_weight=w_test)
        aucs.append(auc(fpr, tpr))
        tprs.append(np.interp(mean_fpr, fpr, tpr))
        ax_roc.plot(fpr, tpr, lw=1, alpha=0.3, label=f'Fold {i}')

    # Save CV ROC Plot
    mean_tpr = np.mean(tprs, axis=0)
    ax_roc.plot(mean_fpr, mean_tpr, color='b', label=f'Mean ROC (AUC = {np.mean(aucs):.4f})', lw=2)
    ax_roc.set(xlabel='FPR', ylabel='TPR', title=f'CV ROC: {mode}')
    ax_roc.legend(loc="lower right"); plt.savefig(f"{out_dir}/cv_roc_{mode}.png"); plt.close()

    # 3. Final Training on ALL Data
    print(f"\n>>> Training final model on all data (100%)...")
    final_spw = np.sum(w[y == 0]) / np.sum(w[y == 1])
    final_model = xgb.XGBClassifier(
        max_depth=5, learning_rate=0.1, n_estimators=500,
        subsample=0.8, colsample_bytree=0.8,
        scale_pos_weight=final_spw, n_jobs=-1, random_state=42,
        eval_metric='logloss'
        )

    final_model.fit(
        X, y, sample_weight=w,
        eval_set=[(X, y)], 
        sample_weight_eval_set=[w],
        verbose=50
    )
    
    # --- Feature Importance Plots ---
    feature_map = {feat: feat.replace(f"Bs{mode}_", "") for feat in features}
    final_model.get_booster().feature_names = [feature_map.get(n, n) for n in final_model.get_booster().feature_names]

    # English comment: --- Feature Importance Plots ---
    for imp_type in ['gain', 'weight']:
        fig, ax = plt.subplots(figsize=(12, 9))
        
        # English comment: 1. Get importance scores and sort them to match XGBoost's internal ordering
        score_dict = final_model.get_booster().get_score(importance_type=imp_type)
        # English comment: Sort by value (descending) and take top 15
        sorted_scores = sorted(score_dict.items(), key=lambda x: x[1], reverse=True)[:15]
        
        # English comment: 2. Prepare data for manual horizontal bar plotting
        # This ensures we have full control over the y-axis labels and positions
        labels = [f.replace(f"Bs{mode}_", "") for f, s in sorted_scores]
        values = [s for f, s in sorted_scores]
        y_pos = np.arange(len(labels))

        # English comment: 3. Plotting manually instead of using plot_importance for better control
        bars = ax.barh(y_pos, values, align='center', height=0.5)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels)
        ax.invert_yaxis()  # English comment: Highest importance on top
        
        # English comment: 4. Add formatted text labels to the end of each bar
        for bar in bars:
            width = bar.get_width()
            if imp_type == 'weight':
                label_text = f'{int(width)}'
            else:
                label_text = f'{width:.2f}'
            
            ax.text(width + (max(values)*0.01), bar.get_y() + bar.get_height()/2, 
                    label_text, va='center', fontsize=10)

        ax.set_xlabel('F score')
        ax.set_title(f'Feature Importance ({imp_type}) - {mode}')
        ax.grid(axis='x', linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        plt.savefig(f"{out_dir}/importance_{imp_type}_{mode}.png", bbox_inches='tight')
        plt.close()


    # --- Correlation Matrix Plots ---

    # English comment: --- Correlation Matrix Plots ---
    for df_temp, name in [(df_sig, 'Signal'), (df_bkg, 'Background')]:
        if df_temp.empty: continue
        plt.figure(figsize=(12, 11)) # Slightly increased height
        
        # English comment: Create shortened labels for plotting by removing prefixes like "BsTau3pTau3p_"
        short_features = [f.replace(f"Bs{mode}_", "") for f in features]
        
        corr = df_temp[features].corr()
        cax = plt.matshow(corr, fignum=1, cmap='RdBu_r', vmin=-1, vmax=1)
        plt.colorbar(cax, fraction=0.046, pad=0.04)
        
        ticks = np.arange(0, len(features), 1)
        # English comment: Use shortened feature names for x and y axis labels
        plt.xticks(ticks, short_features, rotation=90, fontsize=9)
        plt.yticks(ticks, short_features, fontsize=9)
        
        # English comment: Add correlation values as text inside the matrix
        for i in range(len(features)):
            for j in range(len(features)):
                plt.text(j, i, f'{corr.iloc[i, j]:.2f}', 
                         ha='center', va='center', color='black', fontsize=7)
        
        plt.title(f'Correlation Matrix {name} ({mode})', pad=30)
        # English comment: Adjust layout to prevent label clipping
        plt.tight_layout()
        plt.savefig(f"{out_dir}/correlation_{name.lower()}_{mode}.png", bbox_inches='tight')
        plt.close()

    # Save final model
    final_model.save_model(f"{out_dir}/model_{mode}_final_cv.bin")
    print(f">>> Final model and all plots saved in: {out_dir}/")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', type=str)
    parser.add_argument('--sig', type=str, required=True)
    parser.add_argument('--bkg', type=str, required=True)
    parser.add_argument('--folds', type=int, default=5)
    args = parser.parse_args()
    
    run_training_cv(args.mode, args.sig, args.bkg, n_folds=args.folds)



