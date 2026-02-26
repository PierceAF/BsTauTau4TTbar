# features.py

# English comment: Define feature lists for each decay mode
FEATURES_DICT = {
    "Tau3pTau1p": [
        "BsTau3pTau1p_iso_ratio",
        "BsTau3pTau1p_leg1_deepFlavLep",
        "BsTau3pTau1p_leg1_deepFlavB",
        "BsTau3pTau1p_leg1_l3dSig",
        "BsTau3pTau1p_leg1_m_rho",
        "BsTau3pTau1p_leg1_mass",
        "BsTau3pTau1p_leg1_vtxProb",
        "BsTau3pTau1p_leg2_pt",
        "BsTau3pTau1p_m_vis",
        "BsTau3pTau1p_bsX",
        "BsTau3pTau1p_bsY",
        "BsTau3pTau1p_lp_doca_sv3p", 
    ],

    "Tau3pTau3p": [
        "BsTau3pTau3p_leg1_mass", 
        "BsTau3pTau3p_leg2_mass", 
        "BsTau3pTau3p_leg1_m_rho", 
        "BsTau3pTau3p_leg2_m_rho", 
        "BsTau3pTau3p_leg1_vtxProb", 
        "BsTau3pTau3p_leg2_vtxProb", 
        "BsTau3pTau3p_leg1_deepFlavLep", 
        "BsTau3pTau3p_leg1_l3dSig", 
        "BsTau3pTau3p_m_vis", 
        "BsTau3pTau3p_m_exact", 
        "BsTau3pTau3p_pt", 
        "BsTau3pTau3p_eta", 
        "BsTau3pTau3p_iso_ratio"],

    "Tau3pTauMu": [
        "BsTau3pTauMu_iso_ratio",
        "BsTau3pTauMu_leg1_deepFlavLep",
        "BsTau3pTauMu_leg1_deepFlavB",
        "BsTau3pTauMu_leg1_flightLen",
        "BsTau3pTauMu_leg1_m_rho",
        "BsTau3pTauMu_leg1_mass",
        "BsTau3pTauMu_leg1_vtxProb",
        "BsTau3pTauMu_leg1_pt",
        "BsTau3pTauMu_m_vis",
        "BsTau3pTauMu_bsX",
        "BsTau3pTauMu_bsY",
        "BsTau3pTauMu_lp_doca_sv3p", 
    ],

    "Tau3pTauEle": [
        "BsTau3pTauEle_iso_ratio",
        "BsTau3pTauEle_leg1_deepFlavLep",
        "BsTau3pTauEle_leg1_deepFlavB",
        "BsTau3pTauEle_leg1_flightLen",
        "BsTau3pTauEle_leg1_m_rho",
        "BsTau3pTauEle_leg1_mass",
        "BsTau3pTauEle_leg1_vtxProb",
        "BsTau3pTauEle_leg1_pt",
        "BsTau3pTauEle_m_vis",
        "BsTau3pTauEle_bsX",
        "BsTau3pTauEle_bsY",
        "BsTau3pTauEle_lp_doca_sv3p", 
    ],

}

# English comment: Define specific pre-selection cuts for each mode
CUT_DICT = {
    "Tau3pTau1p": "1",
    "Tau3pTau3p": "BsTau3pTau3p_m_exact != -1",
    "Tau3pTauMu": "1",
    "Tau3pTauEle": "1"
}

# English comment: Common branches needed for all modes (not features)
BASE_VARS = ['is_true_signal', 'pt', 'L1PreFiringWeight_Nom', 'genWeight', 'puWeight']


