# bTaggingEfficiencyMapAnalyzer
## Scripts for calculation of MC b-tagging efficiency after ntuplization*
The efficiency maps are calculated for each WP and flavor following the recommendations: https://twiki.cern.ch/twiki/bin/view/CMS/BTagSFMethods#b_tagging_efficiency_in_MC_sampl

The TH1 for pT and eta (and the corresponding TH2) histograms are obtained using: 
```
python BTaggingEfficiencyMapAnalyzer.py --input_file INPUT_FILE --year YEAR --output_dir OUTPUT_DIR
```
The script fetches the output file generated from the nano-AOD tools (https://github.com/ttXcubed/nanoAOD-tools) and calculates the histograms for each b-tagging working point and jet flavor.
The script is executed per single file (process) (see below for condor parallel processing).
*Suggestions:* it can be useful to add all the files/process together using (for example) `hadd BTaggingEfficiencyMapAnalyzer_output_after2OS.root *ALL_THE_OUTPUTS_FROM_nanoAOD-tools.root`.

The outputs of the latter are then processed to obtain the efficiencies (as a function of pT, eta) by:
```
makeBTaggingEfficiencyMap.py --input_file INPUT_FILE --year YEAR --output_dir OUTPUT_DIR
```
The latter produces the output root file for each process. The files contain the numerator, denominator and efficiency 2D plots for each flavor and tagging WP.

## Condor submission
The first script can be executed in parallel for multiple files using HTCondor. 
```
cd condor_jobs_submission
python BTaggingEfficiencies_condor_template.py --year YEAR --output_dir OUTPUT_DIR
condor_submit BTaggingEfficiencies_condor_submission.sub
```