#!/usr/bin/env python
# File name: pandas_make_alignment.py
# Author: Matt Robinson
# Date created: 06/05/2017
# Date last modified: 06/05/2017
# Python Version: 3.6
"""
Description:

Usage: python pandas_make_alignment.py pdbfile.pdb pdbseq.seq fastafile.fasta

Note: the PDB file must be in the same directory as this script.
"""
import sys
import re
import os 
from biopandas.pdb import PandasPdb
import pandas as pd

with open(sys.argv[2]) as pdb_seq_file:
    pdb_seq_data = pdb_seq_file.readlines()

with open(sys.argv[3]) as fasta_file:
    full_seq_data = fasta_file.readlines()

#Use biopandas to create pandas dataframes of PDB info
ppdb = PandasPdb()
ppdb.read_pdb(sys.argv[1]) 
atom_df = ppdb.df['ATOM']
hetatm_df = ppdb.df['HETATM']
others_df = ppdb.df['OTHERS'] #pandas dataframe with all the non-atom info in PDB file

#get the last atom number before the ligands
last_atom_num= atom_df['atom_number'].iloc[-1]

#make atom_df so it contains both atoms and hetatms
atom_df = pd.concat([hetatm_df, atom_df])
#sort based on atom_number so it's in order
atom_df = atom_df.sort_values(by=['atom_number'])
#reset the indicies of the df
#atom_df = atom_df.reset_index(drop=True)
#take out water molecules
atom_df = atom_df.loc[atom_df['residue_name'] != 'HOH']
#reset the indicies of the df
atom_df = atom_df.reset_index(drop=True)

#need to take out the ligand hetatms because they also have chain ID
last_atom_idx = atom_df.loc[atom_df['atom_number']==last_atom_num].index
atom_df = atom_df.iloc[:last_atom_idx[0]+1]

#take off file ending to get pdb id
pdb_id = os.path.splitext(os.path.basename(sys.argv[1]))[0]

#list so can make chain dictionaries later
chain_labels_l = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']

#make a dictionary for translating chain id's into A,B,C,D... as Modeller likes
id_dict = {}
id_list = list(atom_df['chain_id'])
alphabet_idx = 0
for i in range(1,len(list(id_list))):
    if id_list[i] != id_list[i-1]:
        id_dict[id_list[i-1]] = chain_labels_l[alphabet_idx] 
        alphabet_idx = alphabet_idx + 1
    if (i == len(list(id_list))-1):
       id_dict[id_list[i]] = chain_labels_l[alphabet_idx]  

#now change atom_df to have these labels
atom_df['chain_id'] = atom_df['chain_id'].apply(lambda x: id_dict[x])


def main():

    #get a dict of all the missing residues, keys are chain id, values are lists
    #missing_res_ls = find_missing_res_l(others_df)
    #get the lists of disconnections
    #missing_seq_ls = get_missing_res()

    pdb_seq = get_pdb_seq(pdb_seq_data)
    full_seq = get_full_seq(full_seq_data)
    #print(full_seq)

    #now trim the full sequence so that the non-crystallized ends are removed
    #full_seq = trim_full_seq(pdb_seq, full_seq)
    #print(pdb_seq)
    #print('\n')
    #print(full_seq)

    #need to trim off ligand of pdb_seq
    ligand_str = trim_ligand_seq(pdb_seq)[1]
    pdb_seq = trim_ligand_seq(pdb_seq)[0]
    #print(pdb_seq)
    #ligand_str = trim_ligand_seq(pdb_seq)[1]
    #print(ligand_str)

    #break the two seqs up chain by chain
    pdb_seq_l = break_into_chains(pdb_seq)
    #print(pdb_seq_l)
    full_seq_l = break_into_chains(full_seq)
    #print(full_seq_l)

    #check if they have the same number of chains
    if not(len(pdb_seq_l) == len(full_seq_l)):
            print("Fasta sequence has incorrect number of chains")
            sys.exit(2)

    #make chain dictionaries, where keys are the chain ids
    pdb_seq_chain_dict = make_chain_dict(pdb_seq_l)
    full_seq_chain_dict = make_chain_dict(full_seq_l)


    #get a dict of all the missing residues, keys are chain id, values are lists
    missing_res_dict = make_missing_res_dict(others_df)

    #get a dict of just the res numbers
    missing_res_num_dict = make_res_num_dict(missing_res_dict)
    #get a dict of just the res letters (1 letter code)
    missing_res_letter_dict = make_res_letter_dict(missing_res_dict)

    #delete empty chains from pdb and fasta dicts
    ### need to test these###
    pdb_seq_chain_dict = {key:pdb_seq_chain_dict[key] for key in pdb_seq_chain_dict if pdb_seq_chain_dict[key]!=[]}
    full_seq_chain_dict = {key:full_seq_chain_dict[key] for key in full_seq_chain_dict if full_seq_chain_dict[key]!=[]}

    #loop over the chains
    for key in pdb_seq_chain_dict:
        print('chain:' + key)

        #get the seqs of this chain 
        chain_pdb_seq = pdb_seq_chain_dict[key]
        chain_full_seq = full_seq_chain_dict[key]
        flank_res_num_l = get_flank_res_num_l(missing_res_num_dict[key])

        #trim the full sequence so that the non-crystallized ends are removed
        #first make list of the chains
        keys_list = list(pdb_seq_chain_dict.keys())
        #also check if it is last sequence and need to take off '* character'
        #print(chain_full_seq)
        if (not(key == keys_list[-1])):
            chain_full_seq = trim_full_seq(chain_pdb_seq, chain_full_seq)
        else:
            chain_full_seq = trim_full_seq(chain_pdb_seq[0:-1], chain_full_seq[0:-1])
            chain_full_seq = chain_full_seq + '*' #add back the '*' end character
        #print(chain_full_seq)

        #loop over the gaps
        for l in flank_res_num_l:

            print('loop:')
            print(l)

            #get the seq residues flanking the break and the residues b/w which break occurs
            flank_seq, gap_res, seq_before, seq_after = get_flank_seq(l,key) 

            # go to next loop if was an index error on the last one
            if flank_seq == '':
                continue

            #make into one letter seq to work with fasta file
            flank_seq = make_one_letter(flank_seq)
            gap_res = make_one_letter(gap_res)
            seq_before = make_one_letter(seq_before)
            seq_after = make_one_letter(seq_after)

            print('seq:' + flank_seq)
            print('gap res:' + gap_res)
            print('seq_before:' + seq_before)
            print('seq_after:' + seq_after)

            chain_pdb_seq = add_gaps(seq_before,seq_after,chain_full_seq,chain_pdb_seq) #perhaps should be moved so dashes don't interfere

        pdb_seq_chain_dict[key] = chain_pdb_seq
        full_seq_chain_dict[key] = chain_full_seq



    # #loop over the disconnections
    # for l in missing_atom_ls:
    #   print(l)

    #   seq_l = get_missing_seq(l)[0] #the seq residues flanking the break
    #   gap_res_l = get_missing_seq(l)[1] #residues b/w which break occurs
    #   seq_before = get_missing_seq(l)[2] #seq before break
    #   seq_after = get_missing_seq(l)[3] #seq after break

    #   #make into one letter seq to work with fasta file
    #   seq = make_one_letter(seq_l)
    #   gap_res = make_one_letter(gap_res_l)
    #   seq_before = make_one_letter(seq_before)
    #   seq_after = make_one_letter(seq_after)

    #   print('seq:' + seq)
    #   print('gap res:' + gap_res)
    #   print('seq_before:' + seq_before)
    #   print('seq_after:' + seq_after)

    #   #loop over the chains
    #   for i in range(len(pdb_seq_l)):
    #       #use seqs defined above to test if in this chain
    #       test_seq = seq
    #       test_seq_before = seq_before
    #       test_seq_after = seq_after

    #       #trim the full sequence so that the non-crystallized ends are removed
    #       #also check if it is last sequence and need to take off '* character'
    #       if (not(i == len(pdb_seq_l) -1)):
    #           full_seq_l[i] = trim_full_seq(pdb_seq_l[i], full_seq_l[i])
    #       else:
    #           full_seq_l[i] = trim_full_seq(pdb_seq_l[i][0:-1], full_seq_l[i][0:-1])
    #           full_seq_l[i] = full_seq_l[i] + '*' #add back the '*' end character

    #       #if there are hetatoms present, need to deal with that by making the '.' part of the sequence
    #       # if ('.' in pdb_seq_l[i]):
    #       #   test_seq, test_seq_before, test_seq_after = get_hetatm_seq(test_seq, pdb_seq_l[i], gap_res)
    #       #   print('test seq:' + test_seq)
    #       #   print('test seq before:' + test_seq_before)
    #       #   print('test seq after:' + test_seq_after)

            # # check that this is the chain with the disconnection
            # if (test_seq in pdb_seq_l[i]):
            #   print('test seq in chain' + str(i))
            #   #now add the gaps in the string
            #   pdb_seq_l[i] = add_gaps(test_seq_before,test_seq_after,full_seq_l[i],pdb_seq_l[i])

    # put seqs back together
    pdb_seq = '/'.join(list(pdb_seq_chain_dict.values()))
    full_seq = '/'.join(list(full_seq_chain_dict.values()))

    #add last character to full_seq
    #full_seq = full_seq

    #add back the ligands
    pdb_seq = pdb_seq[0:-1] + ligand_str + '*'
    full_seq = full_seq[0:-1] + ligand_str + '*'

    #split both of the seqs into 75 character substrings for .pir format
    pdb_seq_substr = split_sequence(pdb_seq)
    full_seq_substr = split_sequence(full_seq)

    #write the output file into the local directory
    aln_file = open((pdb_id + "_alignment.ali"),"w+")

    for line in pdb_seq_data[0:3]:
        aln_file.write(line)

    for substr in pdb_seq_substr:
        aln_file.write(substr + '\n')

    aln_file.write('>P1;' + pdb_id + '_fill' + '\n') #header for full seq
    aln_file.write('sequence:::::::::'+'\n')

    for substr in full_seq_substr[0:-1]:
        aln_file.write(substr + '\n')
    aln_file.write(full_seq_substr[-1]) #don't want to end with newline character

    aln_file.close()


#find the atoms between which residues are missing.
# def get_atoms(chop_data):
#     atom_ls = []
#     for line in chop_data:
#         if (line[0:16] == '   disconnection'):
#             atoms = []
#             atoms_str = line.split('atoms ',1)[1]
#             atoms_str = atoms_str.split(' is',1)[0]
#             atom1 = atoms_str.split(', ',1)[0]
#             atom2 = atoms_str.split(', ',1)[1]
#             atoms.append(int(atom1))
#             atoms.append(int(atom2))
#             atom_ls.append(atoms)
#     return atom_ls

def get_pdb_seq(pdb_seq_data):
    pdb_seq = ""
    seq_data = pdb_seq_data[3:]
    for line in seq_data:
        line = line.rstrip()
        pdb_seq = pdb_seq + line
    #remove the break character '/'
    #pdb_seq = re.sub('/','',pdb_seq)
    return pdb_seq

def get_full_seq(fasta_data):
    full_seq = ''
    for line in fasta_data:
        if not(line[0] == '>'):
            line = line.rstrip() #I could have just messed up some crap with this
            full_seq = full_seq + line
        if (line[0] == '>'): #if have new chain
            full_seq = full_seq + '/' #to indicate chain break

    #get rid of beginning '/'        
    if full_seq[0] == '/':
        full_seq = full_seq[1:] #get rid of beginning '/'

    return full_seq + '*'

def trim_full_seq(pdb_seq, full_seq):
    pdb_letters = pdb_seq
    #trim off the front
    for i in range(len(full_seq)):
        if (full_seq[i:i+5] == pdb_letters[0:5]):
            full_seq = full_seq[i:]
            break #needed so proper length
    #trim off the back (make sure * is not present or will mess it up)
    for j in reversed(range(len(full_seq)+1)):
        if (full_seq[j-5:j] == pdb_letters[(len(pdb_letters)-5):]):
            full_seq = full_seq[0:j]
            break
    return full_seq

# def get_missing_seq(missing_atoms_l):
#     #make biopandas dataframe from pdb
#     #ppdb.read_pdb(sys.argv[2]) #need to fill this in.

#     l = missing_atoms_l # for convenience of writing

#     #get the index of the pandas df that this atom is at
#     first_atom_idx = (atom_df.loc[atom_df['atom_number'] ==  l[0]].index)[0]
#     second_atom_idx = (atom_df.loc[atom_df['atom_number'] ==  l[1]].index)[0]

#     # when selecting residues, need to know if at end of chain, don't want to call out of bounds idx
#     if (first_atom_idx-40 < 0):
#         lower_bound = 0
#     else:
#         lower_bound = first_atom_idx-40

#     if (second_atom_idx+40 >= atom_df.shape[0]):
#         upper_bound = atom_df.shape[0] - 1
#     else:
#         upper_bound = second_atom_idx+40

#     #get residue number of res with first atom
#     first_atom_res_num = atom_df.loc[atom_df['atom_number'] ==  l[0],'residue_number']
#     first_atom_res_num = int(first_atom_res_num.values)
#     #get residue number of res with second atom
#     second_atom_res_num = atom_df.loc[atom_df['atom_number'] ==  l[1],'residue_number']
#     second_atom_res_num = int(second_atom_res_num.values)

#     # get lists of the residues (and their numbers) before and after the missing residues
#     res_before_l = list(atom_df.loc[lower_bound:first_atom_idx]['residue_name'])
#     resnum_before_l = list(atom_df.loc[lower_bound:first_atom_idx]['residue_number'])

#     res_after_l = list(atom_df.loc[second_atom_idx:upper_bound]['residue_name'])
#     resnum_after_l = list(atom_df.loc[second_atom_idx:upper_bound]['residue_number'])

#     # add the residue names to the list, and make sure only once per residue
#     res_before = []
#     res_before.append(res_before_l[0])
#     for i in range(1,len(res_before_l)):
#         if ((not(resnum_before_l[i] == resnum_before_l[i-1]))): #checking if same aa, is diff res
#             res_before.append(res_before_l[i])

#     # add the residue names to the list, and make sure only once per residue
#     res_after = []
#     res_after.append(res_after_l[0])
#     for i in range(1,len(res_after_l)):
#         if ((not(resnum_after_l[i] == resnum_after_l[i-1]))):
#             res_after.append(res_after_l[i])

#     #Need to check if the break occured w/in a res or between two separate res
#     if (first_atom_res_num == second_atom_res_num):
#         res_after = res_after[1:] #take off the first res, which is repeated
#         gap_res = [res_before[-1],res_after[0]] #make next rest in seq the second gap res

#     else: #they are different res
#         gap_res = [res_before[-1],res_after[0]]

#     merged_seq = res_before + res_after

#     return merged_seq, gap_res, res_before, res_after

def make_one_letter(res_l):
    # Amino acid 3-to-1 letter code dictionary.
    aaDict = dict({'ALA': 'A', 
                    'ARG': 'R', 'ASN': 'N',
                    'ASP': 'D', 'CYS': 'C',
                    'GLN': 'Q', 'GLU': 'E', 
                    'GLY': 'G', 'HIS': 'H',
                    'ILE': 'I', 'LEU': 'L', 
                    'LYS': 'K', 'MET': 'M', 
                    'PHE': 'F', 'PRO': 'P', 
                    'SER': 'S', 'THR': 'T', 
                    'TRP': 'W', 'TYR': 'Y', 
                    'VAL': 'V'})
    #make the lift one letter
    one_letter_code_seq = []
    for res in res_l:
        #check if it is a natural amino acid
        if res in list(aaDict):
            one_letter_code_seq.append(aaDict[res])
        else:
            one_letter_code_seq.append('.') #for HETATMS (unnatural aa's)

    #now make the list one string
    seq_str = ''.join(one_letter_code_seq)
    return seq_str

# def get_hetatm_seq(merged_seq,pdb_seq,gap_res):
#     for i in range(len(merged_seq), len(pdb_seq)):
#         test_seq = pdb_seq[0:i].replace('.','')
#         if (test_seq[len(test_seq)-len(merged_seq):] == merged_seq):
#             merged_seq = pdb_seq[i-len(merged_seq):i]
#             print(merged_seq + '  ' + str(i))
#             break

#     seq_before = merged_seq.split(gap_res)[0] + gap_res[0]
#     seq_after = gap_res[1] + merged_seq.split(gap_res)[1]

#     return merged_seq, seq_before, seq_after



#def find_missing_length(seq_before,full_seq):
    #find where to insert gap
    #gap_idx = full_seq.find(seq_before)

def insert_dashes(string, index, num):
    dash_str = ''
    for i in range(num):
        dash_str = dash_str + '-'
    return string[:index] + dash_str + string[index:]

#Add dashes where the missing residues are in the pdb_seq
def add_gaps(seq_before,seq_after,full_seq,pdb_seq):
    #first turn the expressiongs into re, this works nicely because '.' is the wildcard character
    seq_before_re = re.compile(seq_before)
    seq_after_re = re.compile(seq_after)
    merged_seq_re = re.compile(seq_before + seq_after)

    full_seq_no_dash = full_seq.replace('-','') ##why did i make the full_seq no dash and not pdb_seq instead?????

    #find where gap begins, need to add back length because gives idx at beginning of str
    begin_gap_idx = re.search(seq_before_re,full_seq_no_dash).start() + len(seq_before)
    #begin_gap_idx = full_seq.find(seq_before) + len(seq_before) #probably wrong

    # find where gap ends
    end_gap_idx = re.search(seq_after_re,full_seq_no_dash).start()
    #end_gap_idx = full_seq.find(seq_after)

    #compute number of dashed
    num_dashes = end_gap_idx - begin_gap_idx
    #find where to insert gap in pdb sequence
    insert_idx = re.search(merged_seq_re,pdb_seq).start() + len(seq_before)
    #insert_idx = pdb_seq.find(seq_before + seq_after) + len(seq_before)

    #make new pdb_seq
    pdb_seq = insert_dashes(pdb_seq,insert_idx,num_dashes)

    return pdb_seq

def split_sequence(seq):
    return re.findall('.{1,75}', seq)

def break_into_chains(seq):
    return seq.split('/')

def trim_ligand_seq(hetatm_seq):
    ligand_str = ''
    seq = hetatm_seq[0:-1] #take off the final *
    new_seq = seq
    for j in reversed(range(len(seq))):
        #if not(seq[j] == '/' or seq[j] == '.'):
        if (seq[j] in chain_labels_l):
            new_seq = seq[0:j+1]
            ligand_str = seq[j+1:]
            break
    new_seq = new_seq + '*'
    return new_seq, ligand_str

# function to take in the others_df and return a list the missing res
def find_missing_res_l(others_df):
    # get df that has only the lines that start with 'REMARK'
    remark_df = others_df.loc[others_df['record_name']=='REMARK']
    # turn this data into a list of lists, which contain strings
    remark_l = list(remark_df['entry'].str.split())
    # find the data for all REMARK 465
    missing_res_ls = []
    new_missing_res_ls = []
    for l in remark_l:
        if (l[0] == '465' and len(l)>=2):
            missing_res_ls.append(l[1:])
    #exit if can't find any missing residues
    if (len(missing_res_ls) == 0):
        print("cannot find any missing residues")
        sys.exit(2)
    # get only the lines that contain the missing residues
    for i in range(len(missing_res_ls)):
        if (not(len(missing_res_ls[i]) == 0)):
            #take all lines after '465 M RES C SSSEQI'
            if (((missing_res_ls[i])[0]) == 'M'):
                #call it something different so it doesn't mess up the size
                new_missing_res_ls = missing_res_ls[i+1:]
    return new_missing_res_ls

# make a dictionary with chain id's as the keys and list of missing res as the values
def make_missing_res_dict(others_df):

    # first, get the missing_res_ls
    missing_res_ls = find_missing_res_l(others_df)
    # initialize dict with empty lists as values
    missing_res_dict = {k:[] for k in chain_labels_l}
    # populate the dict based on chain id
    for l in missing_res_ls:
        missing_res_dict[id_dict[l[1]]].append([l[0],l[2]])
    # now seperate into loops, based on if res_num is sequential
    missing_res_dict_tmp = {k:[] for k in chain_labels_l}
    #loop over dictionary
    for key in missing_res_dict: 
        start_idx = 0
        for i in range(1,len(missing_res_dict[key])):
            res_num = int(missing_res_dict[key][i][1])
            prev_res_num = int(missing_res_dict[key][i-1][1])
            # if res_nums are not sequential, then end of loop
            if (res_num != prev_res_num + 1):
                missing_res_dict_tmp[key].append(missing_res_dict[key][start_idx:i])
                start_idx = i
            # if last residue, then end of loop
            if (i == len(missing_res_dict[key])-1):
                missing_res_dict_tmp[key].append(missing_res_dict[key][start_idx:i+1])
    missing_res_dict = missing_res_dict_tmp
    return missing_res_dict

# make a dictionary of only the residue numbers from missing_res_dict
def make_res_num_dict(missing_res_dict):

    # initialize the dict values to empty lists
    missing_res_num_dict = {k:[] for k in chain_labels_l}

    for key in missing_res_dict:
        for missing_loop_l in missing_res_dict[key]:
            loop_res_num_l = []
            for res in missing_loop_l:
                res_num = int(res[1])
                loop_res_num_l.append(res_num)

            missing_res_num_dict[key].append(loop_res_num_l)

    return missing_res_num_dict
            
# make a dictionary of only the residue letters (1 letter code) from missing_res_dict
def make_res_letter_dict(missing_res_dict):

    # initialize the dict values to empty lists
    missing_res_letter_dict = {k:[] for k in chain_labels_l}

    for key in missing_res_dict:
        for missing_loop_l in missing_res_dict[key]:
            loop_res_letter_l = []
            for res in missing_loop_l:
                res_letter = res[0]
                loop_res_letter_l.append(res_letter)

        missing_res_letter_dict[key].append(loop_res_letter_l)

    # turn 3 letter code into one letter code, and also turn list into str
    one_letter_dict = {k:[] for k in chain_labels_l}
    for key in missing_res_letter_dict:
        for l in missing_res_letter_dict[key]:
            seq_str = make_one_letter(l)
            one_letter_dict[key].append(seq_str)

    return one_letter_dict

#code to turn list of chain seqs into a dictionary where keys are chain ids 
def make_chain_dict(seq_l):
    chain_dict = {k:[] for k in chain_labels_l}

    letter_idx=0
    for chain in seq_l:
        chain_letter = chain_labels_l[letter_idx]
        chain_dict[chain_letter] = chain
        letter_idx = letter_idx + 1

    return chain_dict

#function to get a list of residues that flank the gaps
def get_flank_res_num_l(missing_res_loops):
    flank_res_l = []
    for loop in missing_res_loops:
        #find the first and last residue of the loop, then go outside by one
        flank_res_l.append([loop[0]-1,loop[-1]+1])
    return flank_res_l

def get_flank_seq(flank_res_num,key):

    first_res_num = flank_res_num[0]
    second_res_num = flank_res_num[1]

    #need to only get rows with the correct chain id

    chain_df = atom_df.loc[atom_df['chain_id']==key]
    #reset the index to 0
    chain_df = chain_df.reset_index(drop=True)

    #l = flank_res_num # for convenience of writing

    #get the first atom_number of the pandas df that this res is at
    try:
        first_atom_idx = (chain_df.loc[chain_df['residue_number'] ==  first_res_num,'atom_number'].index)[0]
        second_atom_idx = (chain_df.loc[chain_df['residue_number'] == second_res_num,'atom_number'].index)[-1]
    #if at the end of a chain    
    except IndexError:
        return '','','',''

    #make sure they are not at the end of the chain:
    if (first_atom_idx == [] or second_atom_idx == []):
        return '','','',''

    # when selecting residues, need to know if at end of chain, don't want to call out of bounds idx
    if (first_atom_idx-40 < 0):
        lower_bound = 0
    else:
        lower_bound = first_atom_idx-40

    if (second_atom_idx+40 >= chain_df.shape[0]):
        upper_bound = chain_df.shape[0] - 1
    else:
        upper_bound = second_atom_idx+40

    # #get residue number of res with first atom
    # first_atom_res_num = atom_df.loc[atom_df['atom_number'] ==  l[0],'residue_number']
    # first_atom_res_num = int(first_atom_res_num.values)
    # #get residue number of res with second atom
    # second_atom_res_num = atom_df.loc[atom_df['atom_number'] ==  l[1],'residue_number']
    # second_atom_res_num = int(second_atom_res_num.values)

    # get lists of the residues (and their numbers) before and after the missing residues
    res_before_l = list(chain_df.loc[lower_bound:first_atom_idx]['residue_name'])
    resnum_before_l = list(chain_df.loc[lower_bound:first_atom_idx]['residue_number'])

    res_after_l = list(chain_df.loc[second_atom_idx:upper_bound]['residue_name'])
    resnum_after_l = list(chain_df.loc[second_atom_idx:upper_bound]['residue_number'])

    # add the residue names to the list, and make sure only once per residue
    res_before = []
    res_before.append(res_before_l[0])
    for i in range(1,len(res_before_l)):
        if ((not(resnum_before_l[i] == resnum_before_l[i-1]))): #checking if same aa, is diff res
            res_before.append(res_before_l[i])

    # add the residue names to the list, and make sure only once per residue
    res_after = []
    res_after.append(res_after_l[0])
    for i in range(1,len(res_after_l)):
        if ((not(resnum_after_l[i] == resnum_after_l[i-1]))):
            res_after.append(res_after_l[i])

    # #Need to check if the break occured w/in a res or between two separate res
    # if (first_atom_res_num == second_atom_res_num):
    #   res_after = res_after[1:] #take off the first res, which is repeated
    #   gap_res = [res_before[-1],res_after[0]] #make next rest in seq the second gap res

    # else: #they are different res
    #   gap_res = [res_before[-1],res_after[0]]

    merged_seq = res_before + res_after
    gap_res = [res_before[-1],res_after[0]]

    return merged_seq, gap_res, res_before, res_after



if __name__ == "__main__":
    main()
