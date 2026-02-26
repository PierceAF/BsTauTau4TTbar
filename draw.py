import ROOT
import os
import sys
import argparse
import numpy as np
from officialStyle import officialStyle
import config_samples
import copy

# English comment: Disable warnings globally to suppress CMSSW/LCG library mismatch noise
import warnings
warnings.filterwarnings("ignore")

# --- Configuration ---
ROOT.gROOT.SetBatch(True)
officialStyle(ROOT.gStyle)
ROOT.gStyle.SetOptTitle(0)
ROOT.gStyle.SetOptStat(0)

LUMI = 59.7  
MC_WEIGHT = "L1PreFiringWeight_Nom * genWeight * puWeight"
Q_MIN = 0.01
Q_MAX = 0.99

def ensure_dir(directory):
    if not os.path.exists(directory): os.makedirs(directory)



import copy

def load_config(mode, use_mva=False):
    """
    Load config from python file, calculate effective cross-sections, 
    and construct full file paths.
    """
    # English comment: Get data from the imported config_samples module
    base_dir = config_samples.BaseDir
    # English comment: Deepcopy to avoid modifying the original config during runtime
    samples = copy.deepcopy(config_samples.Samples)
    selections = config_samples.Selections
    
    mode_selection = selections.get(mode, "1")
    
    for sname, info in samples.items():
        # English comment: Replace {MODE} placeholder in file path and cut strings
        info["file"] = info["file"].replace("{MODE}", mode)
        info["cut"] = info["cut"].replace("{MODE}", mode)
        
        # --- Handle Cross-section ---
        if "xsec_info" in info:
            xs = info["xsec_info"].get("cross_section", 1.0)
            eff = info["xsec_info"].get("filter_eff", 1.0)
            info["xsec"] = xs * eff
        elif "xsec" not in info:
            info["xsec"] = 1.0

        # --- Handle File Paths ---
        rel_path = info["file"]
        if use_mva:
            rel_path = rel_path.replace(".root", "_mva.root")
        
        info["file"] = os.path.join(base_dir, rel_path)
    
    return samples, mode_selection


def get_auto_range(tree, var, cut):
    """Calculates the [1%, 99%] quantile range by scanning the actual data."""
    # English comment: Using GetMinimum/GetMaximum is unreliable in some ROOT files (returns 0).
    # We use tree.Draw to find the actual min/max of the distribution accurately.
    tree.Draw(f"{var}>>htemp_range", cut, "goff")
    htemp = ROOT.gDirectory.Get("htemp_range")
    
    if not htemp or htemp.GetEntries() == 0:
        return None, None
        
    raw_min = htemp.GetXaxis().GetXmin()
    raw_max = htemp.GetXaxis().GetXmax()

    # English comment: Now compute quantiles for a clean plot range
    # We create a high-resolution temp histogram to find the 1% and 99% points
    tmp_h = ROOT.TH1D("tmp_h", "", 1000, raw_min, raw_max)
    tree.Project("tmp_h", var, cut)
    
    probs = np.array([Q_MIN, Q_MAX], dtype=float)
    q_values = np.array([0.0, 0.0], dtype=float)
    tmp_h.GetQuantiles(2, q_values, probs)
    
    # English comment: Cleanup temp histograms from memory
    tmp_h.Delete()
    htemp.Delete()
    
    return q_values[0], q_values[1]


def write_datacard(filename, shapes_file, processes, rates, bin_name, observation=-1):
    """Generates a CMS Combine datacard."""
    n_all = len(processes)
    n_bkg = n_all - 1

    with open(filename, 'w') as f:
        f.write("imax 1  number of channels\n")
        f.write("jmax {}  number of backgrounds\n".format(n_bkg))
        f.write("kmax * number of nuisance parameters\n")
        f.write("-" * 60 + "\n")
        f.write("shapes * * {} $CHANNEL/$PROCESS $CHANNEL/$PROCESS_$SYSTEMATIC\n".format(os.path.basename(shapes_file)))
        f.write("-" * 60 + "\n")
        f.write("bin {}\n".format(bin_name))
        f.write("observation {}\n".format(observation)) # Change: Use the actual observation yield
        f.write("-" * 60 + "\n")
        
        f.write("{:<15}".format("bin"))
        for _ in range(len(processes)): f.write(" {:<15}".format(bin_name))
        f.write("\n")

        f.write("{:<15}".format("process"))
        for p in processes: f.write(" {:<15}".format(p))
        f.write("\n")

        f.write("{:<15}".format("process"))
        for i in range(len(processes)): f.write(" {:<15}".format(i))
        f.write("\n")

        f.write("{:<15}".format("rate"))
        for r in rates: f.write(" {:<15.4f}".format(r))
        f.write("\n")
        f.write("-" * 60 + "\n")
        
        f.write("{:<12} {:<6}".format("lumi", "lnN"))
        for _ in range(n_all): 
            f.write(" {:<10}".format("1.025"))

        f.write("\n")

def plot_all(mode, samples, global_selection, datacard_var=None):
    output_dir = f"plots/plots_{mode}"
    ensure_dir(output_dir)

    datacard_dir = f"datacard"
    ensure_dir(datacard_dir)

    target_prefixes = [f"Bs{mode}"]
    bin_name = mode 

    first_sample_key = list(samples.keys())[0]
    first_file_path = samples[first_sample_key]["file"]
    
    f_sample = ROOT.TFile.Open(first_file_path)
    if not f_sample: 
        print(f"Error: Could not open first sample {first_file_path}")
        return
    tree_sample = f_sample.Get("tree")

    variables = []
    for b in tree_sample.GetListOfBranches():
        name = b.GetName()
        if (any(name.startswith(p) for p in target_prefixes) or "mva_score" in name) and "_is_true_signal" not in name:
            variables.append(name)
    f_sample.Close()

    for var in sorted(variables):

        if datacard_var is not None and var != datacard_var:
            continue
            
        print(f"\n>>> Variable: {var}")
        v_min, v_max = 999999, -999999
        valid_var = False
        
        # --- Range Determination ---
        for name, info in samples.items():

            f = ROOT.TFile.Open(info["file"])
            if not f: continue
            t = f.Get("tree")
            if not t:
                f.Close()
                continue
            combined_cut = f"({global_selection}) && ({info['cut']})"

#            print(f"DEBUG: Tree entries: {t.GetEntries()}")
            q_low, q_high = get_auto_range(t, var, combined_cut)
            if q_low is not None:
                v_min, v_max = min(v_min, q_low), max(v_max, q_high)
                valid_var = True
            f.Close()

        if not valid_var: continue
        # English comment: Add 10% padding to the range
        v_min, v_max = v_min - (v_max-v_min)*0.1, v_max + (v_max-v_min)*0.1

        hists, dc_processes, dc_rates, dc_hists, max_y = [], [], [], [], 0
        
        # --- Filling Histograms ---
        for name, info in samples.items():

            f = ROOT.TFile.Open(info["file"])
            t = f.Get("tree")
            h_name = f"h_{name}_{var}"
            h_temp = ROOT.TH1D(h_name, f";{var};Normalized", 50, v_min, v_max)
            combined_cut = f"({global_selection}) && ({info['cut']})"
            w_str = f"(({combined_cut}) * ({MC_WEIGHT}))" if info["isMC"] else f"({combined_cut})"
            t.Project(h_name, var, w_str)
            
            # Overflow/Underflow
            nbins = h_temp.GetNbinsX()
            h_temp.SetBinContent(1, h_temp.GetBinContent(1) + h_temp.GetBinContent(0))
            h_temp.SetBinContent(nbins, h_temp.GetBinContent(nbins) + h_temp.GetBinContent(nbins + 1))
            h_temp.SetDirectory(0) 

            if info["isMC"]:
                h_sumw = f.Get("h_genEventSumw")
                # English comment: Scale by xsec (calculated in load_config), Lumi, and sum of weights
                scale = info["xsec"] * LUMI * 1000. / (h_sumw.GetBinContent(1) if h_sumw else 1.0)
                h_temp.Scale(scale)

            total_yield = h_temp.GetSumOfWeights()
            
            # Data for Datacard
            if var == datacard_var:
                dc_processes.append(name)
                dc_rates.append(total_yield)
                h_dc = h_temp.Clone(f"{name}")
                h_dc.SetDirectory(0)
                dc_hists.append(h_dc)

            # Data for Plotting
            if total_yield > 0:
                h_plot = h_temp.Clone(h_name + "_plot")
                h_plot.SetDirectory(0)
                h_plot.Scale(1.0 / total_yield)
                h_plot.SetLineColor(info["color"])
                h_plot.SetLineWidth(2)
                # English comment: Attach label and yield for legend
                h_plot.sample_label = info.get("label", name)
                h_plot.original_yield = total_yield
                hists.append(h_plot)
                if h_plot.GetMaximum() > max_y: max_y = h_plot.GetMaximum()
            f.Close()

        # --- Draw and Save Plot ---
        if hists:
            canvas = ROOT.TCanvas(f"c_{var}", "", 800, 700)
            canvas.SetLeftMargin(0.15)
            leg = ROOT.TLegend(0.40, 0.70, 0.92, 0.88)
            leg.SetBorderSize(0)
            leg.SetTextSize(0.03)
            for i, h in enumerate(hists):
                h.SetMaximum(max_y * 1.4)
                h.SetMinimum(0)
                h.Draw("HIST" if i == 0 else "HIST SAME")
                leg.AddEntry(h, f"{h.sample_label} ({h.original_yield:.1f})", "l")
            leg.Draw()
            canvas.Print(f"{output_dir}/{var}_comp.png")
            canvas.Close()

        # --- Datacard Creation ---

        # --- Datacard Creation ---
        if var == datacard_var and dc_hists:
            shapes_file = f"{datacard_dir}/shapes_{mode}.root"
            f_shapes = ROOT.TFile.Open(shapes_file, "RECREATE")
            f_shapes.mkdir(bin_name)
            f_shapes.cd(bin_name)
            
            # English comment: Create data_obs by summing all background histograms (Asimov dataset)
            # This avoids errors when real data is not yet available.
            h_data_obs = None
            
            for i, h in enumerate(dc_hists):
                h.Write()
                # English comment: Assuming signal sample name contains 'Signal'. 
                # Sum only backgrounds for data_obs.
                if "Signal" not in dc_processes[i]:
                    if h_data_obs is None:
                        h_data_obs = h.Clone("data_obs")
                        h_data_obs.SetDirectory(0)
                    else:
                        h_data_obs.Add(h)
            
            # English comment: If no backgrounds found, just clone the first histogram to avoid null
            if h_data_obs is None and len(dc_hists) > 0:
                h_data_obs = dc_hists[0].Clone("data_obs")
            
            if h_data_obs:
                h_data_obs.Write()

            obs_yield = h_data_obs.GetSumOfWeights() if h_data_obs else -1
            f_shapes.Close()
            
            # English comment: Ensure dc_processes and dc_rates include data_obs for the datacard text file
            # However, Combine usually reads observation from the shape file, 
            # so 'observation -1' in write_datacard is already fine.
            write_datacard(f"{datacard_dir}/datacard_{mode}.txt", shapes_file, dc_processes, dc_rates, bin_name, observation=obs_yield)
            print(f">>> Datacard created for {datacard_var} (Observed: {obs_yield:.2f})")


            
#        if var == datacard_var and dc_hists:
#            shapes_file = f"{datacard_dir}/shapes_{mode}.root"
#            f_shapes = ROOT.TFile.Open(shapes_file, "RECREATE")
#            f_shapes.mkdir(bin_name)
#            f_shapes.cd(bin_name)
#            for h in dc_hists: h.Write()
#            f_shapes.Close()
#            write_datacard(f"{datacard_dir}/datacard_{mode}.txt", shapes_file, dc_processes, dc_rates, bin_name)
#            print(f">>> Datacard created for {datacard_var}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', type=str)
    parser.add_argument('--mva', action='store_true')
    parser.add_argument('--datacard_var', type=str, default=None)
    args = parser.parse_args()
    
    # English comment: Load using the new python-based config function
    samples_config, mode_selection = load_config(args.mode, use_mva=args.mva)
    plot_all(args.mode, samples_config, mode_selection, datacard_var=args.datacard_var)

    
