
BaseDir = "/eos/cms/store/group/phys_bphys/ytakahas/bstautau/flat/"

Samples = {

    "Signal": {
        "file": "bstautau/Bs{MODE}_Flat.root",
        "cut": "1",
        "label": "B_{s} #rightarrow #tau#tau (Match)",
        "color": 633,
        "xsec_info": {
            "cross_section": 830.0,
            "filter_eff": 0.16
        },
        "isMC": True
    },

#    "Signal_true": {
#        "file": "bstautau/Bs{MODE}_Flat.root",
#        "cut": "Bs{MODE}_is_true_signal == 1",
#        "label": "B_{s} #rightarrow #tau#tau (Match)",
#        "color": 633,
#        "xsec_info": {
#            "cross_section": 830.0,
#            "filter_eff": 0.16
#        },
#        "isMC": True
#    },
#
#    "Signal_false": {
#        "file": "bstautau/Bs{MODE}_Flat.root",
#        "cut": "Bs{MODE}_is_true_signal == 0",
#        "label": "B_{s} #rightarrow #tau#tau (Non-match)",
#        "color": 601,
#        "xsec_info": {
#            "cross_section": 830.0,
#            "filter_eff": 0.16
#        },
#        "isMC": True
#    },

    "tt_semileptonic": {
        "file": "tt_semileptonic/Bs{MODE}_Flat.root",
        "cut": "1",
        "label": "tt semileptonic",
        "color": 418,
        "xsec_info": {
            "cross_section": 366.29,
            "filter_eff": 1.0
        },
        "isMC": True
    }
}

Selections = {
    "Tau3pTau1p": "nj>=4 && nbj>=2",
    "Tau3pTau3p": "nj>=4 && nbj>=2 && BsTau3pTau3p_m_exact!=-1",
    "Tau3pTauMu": "nj>=4 && nbj>=2",
    "Tau3pTauEle": "nj>=4 && nbj>=2"
}

