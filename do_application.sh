export PYTHONPATH=/cvmfs/cms.cern.ch/el8_amd64_gcc11/external/py3-numpy/1.24.3-65e90ecb70381ce16713acda444b17a0/lib/python3.9/site-packages:$PYTHONPATH

base="/eos/cms/store/group/phys_bphys/ytakahas/bstautau/flat/tt_semileptonic/"

for mode in Tau3pTau1p Tau3pTau3p Tau3pTauMu Tau3pTauEle
#for mode in Tau3pTauMu
do
    python3 mva_application.py ${mode} --input ${base}/Bs${mode}_Flat.root --model mva/mva_results_${mode}_CV/model_${mode}_final_cv.bin --output ${base}/Bs${mode}_Flat_mva.root

done
