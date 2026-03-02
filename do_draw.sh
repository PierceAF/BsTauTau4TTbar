#for mode in Tau3pTau1p Tau3pTauMu Tau3pTauEle Tau3pTau3p
#for mode in Tau3pTauMu
for mode in Tau3pTauEle Tau3pTau3p Tau3pTau1p Tau3pTauMu
    do
	python3 draw.py ${mode} --mva --datacard_var Bs${mode}_mva_score
done
