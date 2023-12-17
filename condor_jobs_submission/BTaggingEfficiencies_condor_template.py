import os
import re
import subprocess
import sys
import argparse
import yaml
from collections import OrderedDict

parser = argparse.ArgumentParser()

parser.add_argument('--year', dest='year', type=str, help='Year')
parser.add_argument('--output_dir', dest='output_dir', type=str, required=True)

args = parser.parse_args()

listOfDataSets = []
listOutputDir = []
yaml_file_dict = {}

file_list = []
process_list = []

ROOT_DIR = '/nfs/dust/cms/user/gmilella/ttX_ntuplizer/'
LOG_REPO = '{}/log'.format(os.getcwd())

ROOT_DIR += 'bkg_'+args.year+'_hotvr/merged/'

for subdir, dirs, files in os.walk(ROOT_DIR):
    if 'log' in subdir:
        continue
    if 'topNN' in subdir:
        continue

    for file in files:
        file_list.append(os.path.join(subdir, file))
print(file_list)

condor_str = ''
with open('BTaggingEfficiencies_condor_submission.sub', 'w+') as condor_f_new: 
    condor_str = 'Executable = BTaggingEfficiencies_executable_BTaggingEfficiencyMapAnalyzer.sh\n'
    condor_str += 'Should_Transfer_Files = NO\nGetenv = True\nRequirements = ( OpSysAndVer == "CentOS7" )\n'

    for i, inFile in enumerate(file_list):
        if '.root' not in inFile: continue

        # --- extracting file name without .root
        match = re.search(r'([^/]+)\.root$', str(inFile))
        if match: 
            process_filename = match.group(1)
        else:
            print("File name not extracted properly...")
            sys.exit()
        # ---

        condor_str += '\narguments = "--input_file {} --output_dir {} --year {}" '.format(inFile, args.output_dir, args.year)

        condor_str += '\nOutput = {}/log_{}.$(Process).out\nError = {}/log_{}.$(Process).err\n''Log = {}/log_{}.$(Process).log\nqueue\n'.format(
            LOG_REPO, process_filename,
            LOG_REPO, process_filename,
            LOG_REPO, process_filename)

    condor_f_new.write(condor_str)

if not os.path.isdir(args.output_dir):
    os.makedirs(args.output_dir)
if not os.path.isdir(LOG_REPO):
    os.makedirs(LOG_REPO)
