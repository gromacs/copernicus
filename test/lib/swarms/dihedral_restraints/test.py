#!/usr/bin/python

from dihedral_restraints import write_restraints

includes=['topol_Protein_chain_A.itp','topol_Protein_chain_B.itp','topol_Protein_chain_C.itp','topol_Protein_chain_D.itp','topol_Other_chain_A2.itp','topol_Other_chain_B2.itp','topol_Other_chain_C2.itp','topol_Other_chain_D2.itp']

write_restraints('start.gro', 'end.gro', 'start.xvg', 'end.xvg', 'topol.top', includes, 20, 'index.ndx', 4)
