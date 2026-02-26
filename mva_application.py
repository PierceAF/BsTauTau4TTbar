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


# English comment: Hotfix for ROOT 6.26/NumPy 1.24+ compatibility.
if not hasattr(np, 'object'):
    np.object = object

import pandas as pd
import ROOT
import xgboost as xgb

# English comment: Suppress specific UserWarnings
warnings.filterwarnings("ignore", category=UserWarning)

# English comment: Import mode configurations
try:
    from features import FEATURES_DICT
except ImportError:
    print("Error: features.py not found.")
    sys.exit(1)

def apply_model(mode, input_file, model_path, output_file, tree_name="tree"):
    """
    Applies the trained XGBoost model to ALL events in the ROOT file.
    No selection cuts are applied during this process.
    """
    if not os.path.exists(model_path):
        print(f"Error: Model file {model_path} not found.")
        return

    # English comment: Load the trained XGBoost model
    model = xgb.XGBClassifier()
    model.load_model(model_path)
    print(f">>> Model loaded: {model_path}")

    features = FEATURES_DICT[mode]

    # English comment: 1. Setup RDataFrame without any Filter
    df_rdf = ROOT.RDataFrame(tree_name, input_file)
    
    # English comment: 2. Extract features for ALL events using AsNumpy
    print(f">>> Extracting features for all events into memory...")
    raw_data = df_rdf.AsNumpy(columns=features)
    
    # English comment: Ensure all columns are converted from RVec objects to flat NumPy arrays
    processed_data = {}
    for feat in features:
        vals = raw_data[feat]
        if len(vals) > 0 and hasattr(vals[0], '__getitem__') and not isinstance(vals[0], (str, bytes)):
            processed_data[feat] = np.array([v[0] if len(v) > 0 else -999.0 for v in vals])
        else:
            processed_data[feat] = vals

    df_inference = pd.DataFrame(processed_data)
    
    # English comment: Fill potential NaN values with -999 to prevent XGBoost inference errors
    df_inference = df_inference.fillna(-999.0)

    # English comment: 3. Run XGBoost Inference
    print(f">>> Running inference on total {len(df_inference)} events...")
    mva_scores = model.predict_proba(df_inference[features])[:, 1].astype(np.float32)

    # English comment: 4. Inject MVA scores back into ROOT via C++ Helper with progress reporter
    if not hasattr(ROOT, 'MVAHelper'):
        ROOT.gInterpreter.ProcessLine('''
            struct MVAHelper {
                std::vector<float> scores;
                size_t idx = 0;
                size_t total = 0;
                MVAHelper() = default;

                float get_score() { 
                    if (idx < scores.size()) {
                        if (idx % 10000 == 0 || idx == total - 1) {
                            printf("    Processing: %3.1f%% (%zu/%zu)\\r", 
                                   (float)idx/total*100.0, idx, total);
                            fflush(stdout);
                        }
                        return scores[idx++];
                    }
                    return -999.0;
                }
                void clear(size_t n) { 
                    idx = 0; 
                    total = n; 
                    scores.clear(); 
                    scores.reserve(n); 
                }
            };
        ''')

    if not hasattr(ROOT, 'mva_helper'):
        ROOT.gInterpreter.ProcessLine('MVAHelper mva_helper;')

    # English comment: Fill the C++ vector
    ROOT.mva_helper.clear(len(mva_scores))
    for s in mva_scores:
        ROOT.mva_helper.scores.push_back(s)

    # English comment: Define new branch for MVA score
    df_final = df_rdf.Define(f"Bs{mode}_mva_score", "mva_helper.get_score()")
    
    print(f">>> Writing ALL events to {output_file} (Snapshot progress will appear below)...")
    # English comment: Snapshot saves every single event from the original tree plus the new branch
    df_final.Snapshot(tree_name, output_file)
    print("") 

    # English comment: 5. Copy h_genEventSumw from the original file to the new file
    f_orig = ROOT.TFile.Open(input_file)
    h_sumw = f_orig.Get("h_genEventSumw")
    if h_sumw:
        print(f">>> Copying h_genEventSumw to {output_file}...")
        f_out = ROOT.TFile.Open(output_file, "UPDATE")
        h_sumw.SetDirectory(f_out)
        h_sumw.Write()
        f_out.Close()
    f_orig.Close()

    print(f">>> Application complete. Total processed: {len(mva_scores)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', type=str)
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--model', type=str, required=True)
    parser.add_argument('--output', type=str, default='output_with_mva.root')
    
    args = parser.parse_args()
    apply_model(args.mode, args.input, args.model, args.output)



