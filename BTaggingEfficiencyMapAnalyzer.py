import os, sys
import re
from argparse import ArgumentParser

import yaml
from yaml.loader import SafeLoader

from array import array

from collections import OrderedDict

import ROOT
ROOT.ROOT.EnableImplicitMT()

ROOT_DIR = '/afs/desy.de/user/g/gmilella/ttX3_post_ntuplization_analysis/ttX_analysis/'

cpp_functions_header = "{}/cpp_functions_header.h".format(ROOT_DIR)
if not os.path.isfile(cpp_functions_header):
    print('No cpp header found!')
    sys.exit()
ROOT.gInterpreter.Declare('#include "{}"'.format(cpp_functions_header))

LUMINOSITY = {
    '2018': 59830, '2017': 41480,
    '2016preVFP': 19500, '2016': 16500
}

LEPTON_SELECTION = ['ee', 'emu', 'mumu']
ELECTRON_ID_TYPE = "MVA"
LEPTON_ID = "loose"

B_TAGGING_WP = {
    '2016preVFP': 
        {'loose': 0.0614, 'medium': 0.3093, 'tight': 0.7221}, #https://btv-wiki.docs.cern.ch/ScaleFactors/UL2016preVFP/
    '2016': 
        {'loose': 0.0480, 'medium': 0.2489, 'tight': 0.6377}, #https://btv-wiki.docs.cern.ch/ScaleFactors/UL2016postVFP/
    '2017': 
        {'loose': 0.0532, 'medium': 0.3040, 'tight': 0.7476}, #https://btv-wiki.docs.cern.ch/ScaleFactors/UL2017/
    '2018': 
        {'loose': 0.0490, 'medium': 0.2783, 'tight': 0.7100}, #https://btv-wiki.docs.cern.ch/ScaleFactors/UL2018/
} 

WEIGHTS_DICT = {
    'ee': 
        "event_weight * {} * {} * {} * {} ".format(
            'trigger_weight_nominal', LEPTON_ID+"_"+ELECTRON_ID_TYPE+"_Electrons_weight_id_nominal", 
            LEPTON_ID+"_"+ELECTRON_ID_TYPE+"_Electrons_weight_recoPtAbove20_nominal", 
            LEPTON_ID+"_"+ELECTRON_ID_TYPE+"_Electrons_weight_recoPtBelow20_nominal"), 
    'emu': 
        "event_weight * {} * {} * {} * {} * {} * {}".format(
            'trigger_weight_nominal', LEPTON_ID+"_"+ELECTRON_ID_TYPE+"_Electrons_weight_id_nominal", 
            LEPTON_ID+"_"+ELECTRON_ID_TYPE+"_Electrons_weight_recoPtAbove20_nominal", 
            LEPTON_ID+"_"+ELECTRON_ID_TYPE+"_Electrons_weight_recoPtBelow20_nominal", 
            "tightRelIso_"+LEPTON_ID+"ID_Muons_weight_id_nominal", 
            "tightRelIso_"+LEPTON_ID+"ID_Muons_weight_iso_nominal"),
    'mumu': 
        "event_weight * {} * {} * {} ".format(
            'trigger_weight_nominal',"tightRelIso_"+LEPTON_ID+"ID_Muons_weight_id_nominal", 
            "tightRelIso_"+LEPTON_ID+"ID_Muons_weight_iso_nominal")
}

VARIABLES_BINNING = OrderedDict()
VARIABLES_BINNING['pt'] = [20, 30, 50, 70, 100, 140, 200, 300, 600, 1000]
VARIABLES_BINNING['eta'] = [0, 0.5, 1.0, 1.5, 2.5]

EVENT_SELECTION = 'after2OS'

class Processor:
    def __init__(self, input_file, output_dir, year):

        self.input_file = input_file
        self.output_dir = output_dir
        self.year = year
        self.lepton_selection = LEPTON_SELECTION

        self.process_name = self._parsing_file()
        self.xsec = self._xsec()
        self.sum_gen_weights = self._sum_gen_weights()
        self.output_file = self._creation_output_file() 


    def _parsing_file(self):
        print("Processing file: {}".format(self.input_file))
        pattern = re.compile(r"merged\/(.*?)_MC")
        match = pattern.search(str(self.input_file))
        if match:
            print("Process name: {}".format(match.group(1)))
            return match.group(1)
        else:
            pattern = re.compile(r"merged\/(.*?)_ntuplizer")
            match = pattern.search(str(self.input_file))
            if match:
                print("Process name: {}".format(match.group(1)))
                return match.group(1)
            else:
                pattern = re.compile(r"merged\/(.*?)_output")
                match = pattern.search(str(self.input_file))
                if match:
                    print("Process name: {}".format(match.group(1)))
                    return match.group(1)
                else:
                    print("No process name found.")
                    sys.exit()

    def _xsec(self):
        process_name = self.process_name
        # if self.is_sgn:
        #     pattern = r"_width\d+"
        #     process_name = re.sub(pattern, '', self.process_name, flags=re.I)

        with open('{}/xsec.yaml'.format(ROOT_DIR)) as xsec_file:
            xsecFile = yaml.load(xsec_file, Loader=SafeLoader)
        if xsecFile[process_name]['isUsed']:
            return xsecFile[process_name]['xSec']
        else:
            print("Xsec for process {} not found in file".format(process_name))
            sys.exit()

    def _sum_gen_weights(self):
        # if self.is_sgn:
        #     root_file = ROOT.TFile(str(self.input_file), 'READ')
        #     sumgenweight = root_file.Get("sumGenWeights")
        #     return sumgenweight.GetVal()
        # else:
        with open("/nfs/dust/cms/user/gmilella/ttX_ntuplizer/bkg_{}_hotvr/merged/sum_gen_weights.yaml".format(self.year)) as sumGenWeights_file:
            sumGenWeightsFile = yaml.load(sumGenWeights_file, Loader=SafeLoader)
            return sumGenWeightsFile[self.process_name]

    def _creation_output_file(self):
        # bkg samples are divided in chunks
        # so the output files should reflect this division
        match = re.search(r'([^/]+)\.root$', str(self.input_file))
        if match: 
            process_filename = match.group(1)
        else:
            print("File name not extracted properly...")
            sys.exit()

        # check if dir exist
        output_dir_path = os.path.join(self.output_dir, str(self.year), EVENT_SELECTION)
        if not os.path.exists(output_dir_path):
            os.makedirs(output_dir_path)

        output_path = os.path.join(output_dir_path, "{}_BTaggingEfficiencyMapAnalyzer_output_{}.root".format(process_filename, EVENT_SELECTION))

        file_out = ROOT.TFile(output_path, 'RECREATE')
        for lep_sel in ['emu', 'ee', 'mumu']:
            ROOT.gDirectory.mkdir(lep_sel)
            file_out.cd()
        print("Output file {}: ".format(file_out))
        return file_out

    def process(self):
        root_df = ROOT.RDataFrame("Friends", str(self.input_file))
        print("Process: {}, XSec: {} pb, Sum of gen weights: {}".format(self.process_name, self.xsec, self.sum_gen_weights))
        # root_df = root_df.Define("event_weight", 
                                #  "genweight * puWeight * {} / {} * {}".format(self.xsec, self.sum_gen_weights, LUMINOSITY[str(self.year)]))

        # adding new columns
        root_df = self._adding_new_columns(root_df)

        for lepton_selection in LEPTON_SELECTION:
            print('\nLepton Selection: {}'.format(lepton_selection))
            root_df_filtered = self._event_selection(root_df, lepton_selection=lepton_selection)

            self.output_file.cd(lepton_selection)

            for flavor_type, flavor in zip(['b', 'c', 'udsg'], [5, 4, 0]):
                print("FLAVOR: ", flavor)

                histo_output = root_df_filtered.Histo2D(
                    ("{}_ak4_flavor_{}_etaVSpt_{}_{}".format(self.process_name, flavor_type, EVENT_SELECTION, lepton_selection), '',
                     len(VARIABLES_BINNING['pt']) - 1, array('d', VARIABLES_BINNING['pt']),
                     len(VARIABLES_BINNING['eta']) - 1, array('d', VARIABLES_BINNING['eta'])),
                    "selectedJets_nominal_flavor_{}_pt".format(flavor_type),
                    "selectedJets_nominal_flavor_{}_eta".format(flavor_type)
                )
                histo_output.Write()
                print("Tot 2D: {}".format(histo_output.Integral()))

                for WP in B_TAGGING_WP[str(self.year)].keys():
                    histo_output = root_df_filtered.Histo2D(
                        ("{}_ak4_btagged_WP_{}_flavor_{}_etaVSpt_{}_{}".format(self.process_name, WP, flavor_type, EVENT_SELECTION, lepton_selection), '',
                        len(VARIABLES_BINNING['pt']) - 1, array('d', VARIABLES_BINNING['pt']),
                        len(VARIABLES_BINNING['eta']) - 1, array('d', VARIABLES_BINNING['eta'])),
                        "selectedBJets_nominal_{}_flavor_{}_pt".format(WP, flavor_type),
                        "selectedBJets_nominal_{}_flavor_{}_eta".format(WP, flavor_type)
                    )
                    histo_output.Write()
                    print("Tot 2D (b-tagging WP {}): {}".format(WP, histo_output.Integral()))

                for var in VARIABLES_BINNING.keys():
                    histo_output = root_df_filtered.Histo1D(
                        ("{}_ak4_flavor_{}_{}_{}_{}".format(self.process_name, flavor_type, var, EVENT_SELECTION, lepton_selection), '', 
                         len(VARIABLES_BINNING[var]) - 1, array('d', VARIABLES_BINNING[var])),
                        "selectedJets_nominal_flavor_{}_{}".format(flavor_type, var),
                    )
                    histo_output.Write()
                    for WP in B_TAGGING_WP[str(self.year)].keys():
                        histo_output = root_df_filtered.Histo1D(
                            ("{}_ak4_btagged_WP_{}_flavor_{}_{}_{}_{}".format(self.process_name, WP, flavor_type, var, EVENT_SELECTION, lepton_selection), '', 
                             len(VARIABLES_BINNING[var]) - 1, array('d', VARIABLES_BINNING[var])),
                            "selectedBJets_nominal_{}_flavor_{}_{}".format(WP, flavor_type, var),
                        )
                        histo_output.Write()

    def _adding_new_columns(self, root_df):
        #### new columns definitions
        for flavor_type, flavor in zip(['b', 'c', 'udsg'], [5, 4, 0]):
            root_df = root_df.Define(
                    "jets_flavor_{}".format(flavor_type),
                    "selectedJets_nominal_hadronFlavour == {}".format(flavor)
                )
            for var in VARIABLES_BINNING.keys():
                root_df = root_df.Define(
                    "selectedJets_nominal_flavor_{}_{}".format(flavor_type, var),
                    "selectedJets_nominal_{}[jets_flavor_{}]".format(var, flavor_type)
                )
                # print("selectedJets_nominal_flavor_{}_{}".format(flavor_type, var))

            # --- b-tagged jets
            for WP in B_TAGGING_WP[str(self.year)].keys():
                root_df = root_df.Define(
                    "bjets_wp_{}_flavor_{}".format(WP, flavor_type),
                    "selectedBJets_nominal_{}_hadronFlavour == {}".format(WP, flavor)
                )
                for var in VARIABLES_BINNING.keys():
                    root_df = root_df.Define(
                        "selectedBJets_nominal_{}_flavor_{}_{}".format(WP, flavor_type, var),
                        "selectedBJets_nominal_{}_{}[bjets_wp_{}_flavor_{}]".format(WP, var, WP, flavor_type)
                    )
            # ---
        ####
        return root_df

    def _event_selection(self, root_df, lepton_selection='ee', n_ak4_outside=2, n_b_outside=2, n_boosted_jets=1, boosted_jets='hotvr'):

        root_df_filtered = root_df.Filter(
            "eventSelection_{}_cut".format(lepton_selection), "os_dilepton_selection"
        )
        # .Filter(
        #     "nselectedJets_nominal_outside_{}>={}".format(boosted_jets, n_ak4_outside), "2ak4_outside"
        # ).Filter(
        #     "nselectedBJets_nominal_outside_{}>={}".format(boosted_jets, n_b_outside), "2b_of_ak4_outside"
        # )

        return root_df_filtered

def main(input_file, output_dir, year):
    # testing
    # input_file = "/nfs/dust/cms/user/gmilella/ttX_ntuplizer/sgn_2018_hotvr/merged/ttX_mass1250_width4_ntuplizer_output.root"
    # input_file = "/nfs/dust/cms/user/gmilella/ttX_ntuplizer/sgn_2018_central_hotvr/merged/TTZprimeToTT_M-750_Width4_output.root"
    # input_file = "/nfs/dust/cms/user/gmilella/ttX_ntuplizer/bkg_2018_hotvr/merged/tt_dilepton_MC2018_ntuplizer_7_merged.root"
    # input_file = "/nfs/dust/cms/user/gmilella/ttX_ntuplizer/data_2018_hotvr/merged/DoubleMuon_2018_B_output.root"
    # output_dir = ROOT_DIR

    processor = Processor(input_file, output_dir, year)
    processor.process()


def parsing_file(file):
    global PROCESS_NAME

    print("Processing file: {}".format(file))

    # Convert file Path to string if it's a Path object
    file_str = file

    pattern = re.compile(r"merged\/(.*?)_MC")
    # Search for the pattern in case of background samples
    match = pattern.search(file_str)  # Use the string representation of the file path
    # Search for the pattern in case of background samples
    match = pattern.search(file_str)
    if match:
        print("Process name: {}".format(match.group(1)))
        PROCESS_NAME = match.group(1)
    else:
        # Search for the pattern in case of signal samples
        pattern = re.compile(r"merged\/(.*?)_ntuplizer")
        match = pattern.search(file_str)
        if match:
            print("Process name: {}".format(match.group(1)))
            PROCESS_NAME = match.group(1)
        else:
            print("No process name found.")
            sys.exit()

    return PROCESS_NAME

#################################################

def parse_args(argv=None):
    parser = ArgumentParser()

    parser.add_argument('--input_file', type=str, required=True,
        help="Input directory, where to find the h5 files")
    parser.add_argument('--output_dir', type=str,
        help="Top-level output directory. "
             "Will be created if not existing. "
             "If not provided, takes the input dir.")
    parser.add_argument('--year', type=int, required=True,
        help='Year of the samples.')

    args = parser.parse_args(argv)

    # If output directory is not provided, assume we want the output to be
    # alongside the input directory.
    if args.output_dir is None:
        args.output_dir = args.input_file

    # Return the options as a dictionary.
    return vars(args)

if __name__ == "__main__":
    args = parse_args()
    main(**args)
