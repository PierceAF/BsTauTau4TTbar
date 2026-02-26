export PYTHONPATH=/cvmfs/cms.cern.ch/el8_amd64_gcc11/external/py3-numpy/1.24.3-65e90ecb70381ce16713acda444b17a0/lib/python3.9/site-packages:$PYTHONPATH

#for mode in Tau3pTauEle Tau3pTauMu Tau3pTau3p Tau3pTau1p
for mode in Tau3pTauEle
do
    python3 mva_training.py ${mode} --sig root/Bs${mode}_Flat.root --bkg root/Bs${mode}_Flat.root
done
