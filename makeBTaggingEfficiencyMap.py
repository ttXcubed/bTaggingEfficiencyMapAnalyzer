import os, sys
import ROOT
from array import array
import argparse
import yaml
import re
from yaml.loader import SafeLoader
from argparse import ArgumentParser


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

VARIABLES_BINNING = {
    'pt': [20, 30, 50, 70, 100, 140, 200, 300, 600, 1000],
    'eta': [0, 0.5, 1.0, 1.5, 2.5]
}

EVENT_SELECTION = "after_2OS"

class Processor:
    def __init__(self, input_file, output_dir, year):

        self.input_file = input_file
        self.output_dir = output_dir
        self.year = year
        self.lepton_selection = LEPTON_SELECTION

        self.output_file = self._creation_output_file() 

        self.all_bkgs = {}

    def _creation_output_file(self):
        # check if dir exist
        self.output_dir = os.path.join(self.output_dir, 'efficiencyMaps')
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        return self.output_dir

    def _merging_bkg(self, root_input_file, lepton_selection='ee'):
        root_input_file.cd(lepton_selection)
        current_dir = ROOT.gDirectory
        for key in current_dir.GetListOfKeys():
            histo = key.ReadObj()
            histo_name = histo.GetName()

            if 'etaVSpt' not in histo_name: continue 

            match = re.search(r'(.*?)_ak4', histo_name)
            if match: process = match.group(1)
            else: continue
            self.all_bkgs.setdefault(process, {})

            match = re.search(r'flavor_(.*?)_', histo_name)
            if match: flavor = match.group(1)
            else: continue
            self.all_bkgs[process].setdefault(flavor, {})

            match = re.search(r'WP_(.*?)_flavor', histo_name)
            if match: 
                wp_btagging = match.group(1)
                if wp_btagging in self.all_bkgs[process][flavor].keys(): 
                    self.all_bkgs[process][flavor][wp_btagging].Add(histo)
                else: self.all_bkgs[process][flavor][wp_btagging] = histo

            else: 
                if 'no_btagged' in self.all_bkgs[process][flavor].keys(): 
                    self.all_bkgs[process][flavor]['no_btagged'].Add(histo)
                else: self.all_bkgs[process][flavor]['no_btagged'] = histo

            # print(process, flavor, wp_btagging)


    def _makeEfficiencyMaps(self, root_input_file):

        self._merging_bkg(root_input_file)

        for process in self.all_bkgs.keys():
            output_file = ROOT.TFile('{}/{}_efficiencyMap.root'.format(self.output_dir, process), 'RECREATE')
            for flavor in self.all_bkgs[process].keys():

                # etaVSpt per jet flavor - no b-tagging applied 
                denominatorIn = self.all_bkgs[process][flavor]['no_btagged']

                # xShift = denominatorIn.GetBinWidth(1)/2.
                # yShift = denominatorIn.GetYaxis().GetBinWidth(1)/2.

                # binsX = array('d', VARIABLES_BINNING['pt'])
                # binsY = array('d', VARIABLES_BINNING['eta'])

                denominatorOut = denominatorIn.Clone('denominator_' + flavor)
                # ROOT.TH2F('denominator_' + flavor, '', (len(binsX)-1), binsX, (len(binsY)-1), binsY)
                denominatorOut.Write()

                for WP in B_TAGGING_WP[str(self.year)].keys():
                    numeratorIn = self.all_bkgs[process][flavor][WP]

                    numeratorOut = numeratorIn.Clone('numerator_' + flavor + '_' + WP)
                    # ROOT.TH2F('numerator_' + flavor + '_' + WP, '', (len(binsX)-1), binsX, (len(binsY)-1), binsY)
                    # efficiencyOut = ROOT.TH2F('efficiency_' + flavor + '_' + WP, '', (len(binsX)-1), binsX, (len(binsY)-1), binsY)

                    # loop over all bins
                    # for binx in range(1, denominatorOut.GetXaxis().GetNbins() + 1):
                    #   for biny in range(1, denominatorOut.GetYaxis().GetNbins() + 1):

                    #     binXMin = denominatorIn.GetXaxis().FindBin(denominatorOut.GetXaxis().GetBinLowEdge(binx)+xShift)
                    #     binXMax = denominatorIn.GetXaxis().FindBin(denominatorOut.GetXaxis().GetBinUpEdge(binx)-xShift)
                    #     binYMinPos = denominatorIn.GetYaxis().FindBin(denominatorOut.GetYaxis().GetBinLowEdge(biny)+yShift)
                    #     binYMaxPos = denominatorIn.GetYaxis().FindBin(denominatorOut.GetYaxis().GetBinUpEdge(biny)-yShift)
                    #     binYMinNeg = denominatorIn.GetYaxis().FindBin(-denominatorOut.GetYaxis().GetBinUpEdge(biny)+yShift)
                    #     binYMaxNeg = denominatorIn.GetYaxis().FindBin(-denominatorOut.GetYaxis().GetBinLowEdge(biny)-yShift)

                    #     denominator = denominatorIn.Integral(binXMin,binXMax,binYMinPos,binYMaxPos)
                    #     denominator = denominator + denominatorIn.Integral(binXMin,binXMax,binYMinNeg,binYMaxNeg)
                    #     numerator = numeratorIn.Integral(binXMin,binXMax,binYMinPos,binYMaxPos)
                    #     numerator = numerator + numeratorIn.Integral(binXMin,binXMax,binYMinNeg,binYMaxNeg)

                    #     if(binx==denominatorOut.GetXaxis().GetNbins()): # also add overflow to the last bin in jet pT
                    #         denominator = denominator + denominatorIn.Integral(binXMax+1,denominatorIn.GetXaxis().GetNbins()+1,binYMinPos,binYMaxPos)
                    #         denominator = denominator + denominatorIn.Integral(binXMax+1,denominatorIn.GetXaxis().GetNbins()+1,binYMinNeg,binYMaxNeg)
                    #         numerator = numerator + numeratorIn.Integral(binXMax+1,numeratorIn.GetXaxis().GetNbins()+1,binYMinPos,binYMaxPos)
                    #         numerator = numerator + numeratorIn.Integral(binXMax+1,numeratorIn.GetXaxis().GetNbins()+1,binYMinNeg,binYMaxNeg)

                    #     denominatorOut.SetBinContent(binx,biny,denominator)
                    #     numeratorOut.SetBinContent(binx,biny,numerator)
                    #     if(denominator>0.): efficiencyOut.SetBinContent(binx,biny,numerator/denominator)

                    # check if there are any bins with 0 or 100% efficiency
                    # for binx in range(1,denominatorOut.GetXaxis().GetNbins()+1):
                    #     for biny in range(1,denominatorOut.GetYaxis().GetNbins()+1):

                    #         efficiency = efficiencyOut.GetBinContent(binx,biny)
                    #         if(efficiency==0. or efficiency==1.):
                    #             print('Warning! Bin({}inx,{}inx) for {} jets has a b-tagging efficiency of {}'.format(binx,biny,flavor,efficiency))

                    efficiencyOut = numeratorIn.Clone('efficiency_' + flavor + '_' + WP)
                    efficiencyOut.Divide(denominatorIn)

                    # set efficiencies in overflow bins
                    for binx in range(1,denominatorOut.GetXaxis().GetNbins()+1):
                        efficiencyOut.SetBinContent(binx, denominatorOut.GetYaxis().GetNbins()+1, efficiencyOut.GetBinContent(binx, denominatorOut.GetYaxis().GetNbins()))
                    for biny in range(1,denominatorOut.GetYaxis().GetNbins()+2):
                        efficiencyOut.SetBinContent(denominatorOut.GetXaxis().GetNbins()+1, biny, efficiencyOut.GetBinContent(denominatorOut.GetXaxis().GetNbins(), biny))

                    numeratorOut.Write()
                    efficiencyOut.Write()
            output_file.Close()

            print('-------------------------------------------------------------------------------------------')
            print('b-tagging efficiency map for ', process)
            output_path = self.output_dir + '/' + process + '_bTaggingEfficiencyMap.root'
            print('successfully created and stored in %s\n'%(output_path))


    def process(self):
        root_input_file = ROOT.TFile(str(self.input_file), 'r')
        print("Process: {}".format(str(self.input_file)))

        self._makeEfficiencyMaps(root_input_file)

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
