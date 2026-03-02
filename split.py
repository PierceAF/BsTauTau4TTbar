import ROOT
import os
import glob
import argparse

# English comment: Enable multi-threading for faster processing
ROOT.EnableImplicitMT()

def get_total_sumw(file_list):
    """Retrieves the total sum of weights from the Runs tree for normalization."""
    runs_chain = ROOT.TChain("Runs")
    for f in file_list:
        runs_chain.Add(f)
    total_sumw = 0.0
    for i in range(runs_chain.GetEntries()):
        runs_chain.GetEntry(i)
        if hasattr(runs_chain, "genEventSumw"):
            total_sumw += runs_chain.genEventSumw
    return total_sumw

def process_modes(input_path, output_dir):
    # English comment: Identify input ROOT files
    if os.path.isdir(input_path):
        input_files = sorted(glob.glob(os.path.join(input_path, "*.root")))
    else:
        input_files = sorted(glob.glob(input_path))

    if not input_files:
        print(f"Error: No ROOT files found in {input_path}")
        return

    print("="*50)
    print(f"Found {len(input_files)} input files")
    for f in input_files:
        print(f" - {f}")
    print("="*50)

    total_sumw = get_total_sumw(input_files)
    print(f"Total genEventSumw: {total_sumw}")

    modes = {
        "BsTau3pTau3p": "BsTau3pTau3p",
        "BsTau3pTau1p": "BsTau3pTau1p",
        "BsTau3pTauMu": "BsTau3pTauMu",
        "BsTau3pTauEle": "BsTau3pTauEle"
    }

    requested_common = [
        "run", "luminosityBlock", "event",
        "puWeight", "L1PreFiringWeight_Nom", "genWeight", 
        "mu1_pt", "mu1_eta", "nj", "nbj", "PuppiMET_pt"
    ]

    for mode_name, prefix in sorted(modes.items()):
        print(f"\n>>> Processing mode: {mode_name}")
        
        df = ROOT.RDataFrame("Events", input_files)
        all_columns = [str(c) for c in df.GetColumnNames()]
        jet_idx_branch = f"{prefix}_leg1_jetIdx"
        
        if jet_idx_branch not in all_columns:
            print(f"Skipping {mode_name}: {jet_idx_branch} not found.")
            continue

        # --- Selection Logic ---
        if mode_name == "BsTau3pTau1p":
            sel_code = f"""
            ROOT::RVec<size_t> indices;
            auto& jet_ids = {jet_idx_branch};
            auto& pts = {prefix}_leg2_pt;
            if (jet_ids.empty()) return indices;
            std::vector<int> unique_jets;
            for (auto j : jet_ids) {{
                if (std::find(unique_jets.begin(), unique_jets.end(), j) == unique_jets.end()) 
                    unique_jets.push_back(j);
            }}
            for (auto j : unique_jets) {{
                int best_idx = -1;
                float max_pt = -1.0;
                for (size_t i = 0; i < jet_ids.size(); ++i) {{
                    if (jet_ids[i] == j) {{
                        if (pts[i] > max_pt) {{
                            max_pt = pts[i];
                            best_idx = i;
                        }}
                    }}
                }}
                if (best_idx != -1) indices.push_back((size_t)best_idx);
            }}
            return indices;
            """
        else:
            sel_code = f"""
            ROOT::RVec<size_t> indices;
            auto& jet_ids = {jet_idx_branch};
            if (jet_ids.empty()) return indices;
            std::vector<int> unique_jets;
            for (auto j : jet_ids) {{
                if (std::find(unique_jets.begin(), unique_jets.end(), j) == unique_jets.end()) 
                    unique_jets.push_back(j);
            }}
            for (auto j : unique_jets) {{
                for (size_t i = 0; i < jet_ids.size(); ++i) {{
                    if (jet_ids[i] == j) {{
                        indices.push_back((size_t)i);
                        break; 
                    }}
                }}
            }}
            return indices;
            """

        # --- Apply Selection ---
        df_selected = df.Define("best_indices", sel_code).Filter("best_indices.size() > 0")

        # English comment: Pre-calculate the correct total for THIS mode after filtering
        total_events_mode = df_selected.Count().GetValue()
        if total_events_mode == 0:
            print(f"No events found for {mode_name}. Skipping...")
            continue

        # --- Progress Monitoring (In-place update) ---
        # English comment: Use \r to overwrite the line and use the mode-specific total
        df_selected = df_selected.Filter(f"""
            static unsigned long long count = 0;
            unsigned long long total = {total_events_mode};
            if (++count % 10000 == 0 || count == total) {{
                float percent = (float)count / total * 100.0;
                printf("\\r>>> {mode_name}: %llu / %llu (%.1f%%) processed...     ", count, total, percent);
                fflush(stdout);
            }}
            if (count == total) {{
                printf("\\n");
                count = 0; // English comment: Reset static counter for the next mode
            }}
            return true;
        """)

        # --- Flattening Branches ---
        prefix_branches = [b for b in all_columns if b.startswith(prefix)]
        for b in prefix_branches:
            df_selected = df_selected.Redefine(b, f"ROOT::VecOps::Take({b}, best_indices)")

        common_branches = [b for b in requested_common if b in all_columns]
        output_branches = common_branches + prefix_branches

        out_file_path = os.path.join(output_dir, f"{mode_name}_Flat.root")
        
        try:
            print(f"Saving to {out_file_path}...")
            # English comment: Snapshot triggers the event loop with our progress Filter
            df_selected.Snapshot("tree", out_file_path, output_branches)

            print(f"\nCopying h_genEventSumw {mode_name}")
            
            f_out = ROOT.TFile.Open(out_file_path, "UPDATE")
            h_sumw = ROOT.TH1D("h_genEventSumw", "Total GenEventSumw", 1, 0, 1)
            h_sumw.SetBinContent(1, float(total_sumw))
            h_sumw.Write()
            f_out.Close()
            print(f"\nSuccessfully finalized {mode_name}")
        except Exception as e:
            print(f"\nFailed to snapshot {mode_name}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flatten NanoAOD by selecting best di-tau per jet")
    parser.add_argument("-i", "--input", required=True, help="Input ROOT file or directory")
    parser.add_argument("-o", "--output_dir", default="root", help="Output directory")
    args = parser.parse_args()

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    process_modes(args.input, args.output_dir)



#    import ROOT
#import os
#import glob
#import argparse
#
## English comment: Enable multi-threading for faster processing
#ROOT.EnableImplicitMT()
#
#def get_total_sumw(file_list):
#    """Retrieves the total sum of weights from the Runs tree for normalization."""
#    runs_chain = ROOT.TChain("Runs")
#    for f in file_list:
#        runs_chain.Add(f)
#    total_sumw = 0.0
#    for i in range(runs_chain.GetEntries()):
#        runs_chain.GetEntry(i)
#        if hasattr(runs_chain, "genEventSumw"):
#            total_sumw += runs_chain.genEventSumw
#    return total_sumw
#
#def process_modes(input_path, output_dir):
#    # English comment: Identify input ROOT files
#    if os.path.isdir(input_path):
#        input_files = sorted(glob.glob(os.path.join(input_path, "*.root")))
#    else:
#        input_files = sorted(glob.glob(input_path))
#
#    if not input_files:
#        print(f"Error: No ROOT files found in {input_path}")
#        return
#
#    print("="*50)
#    print(f"Found {len(input_files)} input files:")
#    for f in input_files:
#        print(f" - {f}")
#    print("="*50)
#
#    total_sumw = get_total_sumw(input_files)
#    print(f"Total genEventSumw: {total_sumw}")
#
#    # English comment: Define mapping of mode names to branch prefixes
#    modes = {
#        "BsTau3pTau3p": "BsTau3pTau3p",
#        "BsTau3pTau1p": "BsTau3pTau1p",
#        "BsTau3pTauMu": "BsTau3pTauMu",
#        "BsTau3pTauEle": "BsTau3pTauEle"
#    }
#
#    requested_common = [
#        "run", "luminosityBlock", "event",
#        "puWeight", "L1PreFiringWeight_Nom", "genWeight", 
#        "mu1_pt", "mu1_eta", "nj", "nbj", "PuppiMET_pt"
#    ]
#
#    for mode_name, prefix in sorted(modes.items()):
#        print(f"\n>>> Processing mode: {mode_name}")
#        
#        df = ROOT.RDataFrame("Events", input_files)
#        
#        # English comment: Get total number of events for progress percentage calculation.
#        # This is a meta-data operation and is typically very fast.
#        total_events = df.Count().GetValue()
#        print(f"Total events to scan: {total_events}")
#
#        all_columns = [str(c) for c in df.GetColumnNames()]
#        jet_idx_branch = f"{prefix}_leg1_jetIdx"
#        
#        if jet_idx_branch not in all_columns:
#            print(f"Skipping {mode_name}: {jet_idx_branch} not found.")
#            continue
#
#        # --- Selection Logic ---
#        if mode_name == "BsTau3pTau1p":
#            sel_code = f"""
#            ROOT::RVec<size_t> indices;
#            auto& jet_ids = {jet_idx_branch};
#            auto& pts = {prefix}_leg2_pt;
#            if (jet_ids.empty()) return indices;
#            std::vector<int> unique_jets;
#            for (auto j : jet_ids) {{
#                if (std::find(unique_jets.begin(), unique_jets.end(), j) == unique_jets.end()) 
#                    unique_jets.push_back(j);
#            }}
#            for (auto j : unique_jets) {{
#                int best_idx = -1;
#                float max_pt = -1.0;
#                for (size_t i = 0; i < jet_ids.size(); ++i) {{
#                    if (jet_ids[i] == j) {{
#                        if (pts[i] > max_pt) {{
#                            max_pt = pts[i];
#                            best_idx = i;
#                        }}
#                    }}
#                }}
#                if (best_idx != -1) indices.push_back((size_t)best_idx);
#            }}
#            return indices;
#            """
#        else:
#            sel_code = f"""
#            ROOT::RVec<size_t> indices;
#            auto& jet_ids = {jet_idx_branch};
#            if (jet_ids.empty()) return indices;
#            std::vector<int> unique_jets;
#            for (auto j : jet_ids) {{
#                if (std::find(unique_jets.begin(), unique_jets.end(), j) == unique_jets.end()) 
#                    unique_jets.push_back(j);
#            }}
#            for (auto j : unique_jets) {{
#                for (size_t i = 0; i < jet_ids.size(); ++i) {{
#                    if (jet_ids[i] == j) {{
#                        indices.push_back((size_t)i);
#                        break; 
#                    }}
#                }}
#            }}
#            return indices;
#            """
#
#        # --- Define Selection and Progress Monitor ---
#        df_selected = df.Define("best_indices", sel_code).Filter("best_indices.size() > 0")
#        
#        # English comment: Injecting progress print with percentage into the event loop via Filter.
#        # This ensures the code is executed even if the result isn't saved in a specific branch.
#        df_selected = df_selected.Filter(f"""
#            static unsigned long long count = 0;
#            static unsigned long long total = {total_events};
#            if (++count % 100000 == 0 || count == total) {{
#                float percent = (float)count / total * 100.0;
#                printf(">>> {mode_name}: %llu / %llu (%.1f%%) processed...\\n", count, total, percent);
#                fflush(stdout);
#            }}
#            return true;
#        """)
#
#        # --- Flattening Branches ---
#        prefix_branches = [b for b in all_columns if b.startswith(prefix)]
#        for b in prefix_branches:
#            df_selected = df_selected.Redefine(b, f"ROOT::VecOps::Take({b}, best_indices)")
#
#        common_branches = [b for b in requested_common if b in all_columns]
#        output_branches = common_branches + prefix_branches
#
#        out_file_path = os.path.join(output_dir, f"{mode_name}_Flat.root")
#        
#        try:
#            print(f"Saving to {out_file_path}...")
#            print(">>> Event loop started. Please wait...")
#            
#            # English comment: Snapshot triggers the event loop and our Filter prints the percentage
#            df_selected.Snapshot("tree", out_file_path, output_branches)
#            
#            f_out = ROOT.TFile.Open(out_file_path, "UPDATE")
#            h_sumw = ROOT.TH1D("h_genEventSumw", "Total GenEventSumw", 1, 0, 1)
#            h_sumw.SetBinContent(1, float(total_sumw))
#            h_sumw.Write()
#            f_out.Close()
#            print(f"Successfully finalized {mode_name}")
#        except Exception as e:
#            print(f"Failed to snapshot {mode_name}: {e}")
#
#if __name__ == "__main__":
#    parser = argparse.ArgumentParser(description="Flatten NanoAOD by selecting best di-tau per jet")
#    parser.add_argument("-i", "--input", required=True, help="Input ROOT file or directory")
#    parser.add_argument("-o", "--output_dir", default="root", help="Output directory")
#    args = parser.parse_args()
#
#    if not os.path.exists(args.output_dir):
#        os.makedirs(args.output_dir)
#
#    process_modes(args.input, args.output_dir)

