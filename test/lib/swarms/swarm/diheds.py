#!/usr/bin/python


dihedsList=[[2,1,5,6],[2,1,5,7],[3,1,5,6],[3,1,5,7],[4,1,5,6],[4,1,5,7],[1,5,7,8],[1,5,7,9],[6,5,7,8],[6,5,7,9],[5,7,9,10],[5,7,9,11],[5,7,9,15],[8,7,9,10],[8,7,9,11],[8,7,9,15],[7,9,11,12],[7,9,11,13],[7,9,11,14],[10,9,11,12],[10,9,11,13],[10,9,11,14],[15,9,11,12],[15,9,11,13],[15,9,11,14],[7,9,15,16],[7,9,15,17],[10,9,15,16],[10,9,15,17],[11,9,15,16],[11,9,15,17],[9,15,17,18],[9,15,17,19],[16,15,17,18],[16,15,17,19],[15,17,19,20],[15,17,19,21],[15,17,19,22],[18,17,19,20],[18,17,19,21],[18,17,19,22],[5,1,7,6],[7,5,9,8],[15,9,17,16],[17,15,19,18]]

atomDict={}
atomDict[1]="CT3"
atomDict[2]="HA"
atomDict[3]="HA"
atomDict[4]="HA"
atomDict[5]="C"
atomDict[6]="O"
atomDict[7]="NH1"
atomDict[8]="H"
atomDict[9]="CT1"
atomDict[10]="HB"
atomDict[11]="CT3"
atomDict[12]="HA"
atomDict[13]="HA"
atomDict[14]="HA"
atomDict[15]="C"
atomDict[16]="O"
atomDict[17]="NH1"
atomDict[18]="H"
atomDict[19]="CT3"
atomDict[20]="HA"
atomDict[21]="HA"
atomDict[22]="HA"

for dihed in dihedsList:
    print "%5s%5s%5s%5s" %(atomDict[dihed[0]],atomDict[dihed[1]],atomDict[dihed[2]],atomDict[dihed[3]])
