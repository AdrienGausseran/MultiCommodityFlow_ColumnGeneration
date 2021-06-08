'''
Created on Jun 5, 2021

@author: agausser
'''

import random

import os


#Return a dict of Nodes : 
#    dictLink["N1"] = ["N2", "N3]    dictLink["N2"] = ["N1"], dictLink["N3"] = ["N1"]
def loadTopo(topoName):


    fileToOpen = os.path.join("..", "instances")
    fileToOpen = os.path.join(fileToOpen, topoName)
    fileToOpen = os.path.join(fileToOpen, "{}.txt".format(topoName))
    
    dictLink = {}
    
    NodePart = False
    LinkPart = False
    
    with open(fileToOpen, "r") as f:
        for line in f :
            
                
            #Nodes part
            if NodePart:
                if line[0] == ")":
                    NodePart = False
                
                else:
                    line = line.split("(")
                    line = line[0].replace(" ", "")
                    line = line.replace("\n", "")
                    dictLink[line] = []
                
            
            
            #Links part
            elif LinkPart:
                if line[0] == ")":
                    break
                else:
                    line = line.split(" ) ")
                    line = line[0].split(" ( ")
                    line = line[1].split(" ")
                    if not (line[1] in dictLink[line[0]]):
                        dictLink[line[0]].append(line[1])
                        dictLink[line[1]].append(line[0])        
                    
            else:
                if line[0] == "N":
                    NodePart = True
                elif line[0] == "L":
                    LinkPart = True          
        

    f.close()
    
    return dictLink


#Create a list of demands
# A demand = (source, destination, bandwidthDemand)
def createInstance(dictLinks, nbDemands):  
    listNodes = list(dictLinks.keys())
    listDemands = []
    
    bwMax = 5
    
    for i in range(1, nbDemands+1):
        
        src = listNodes[random.randint(0, len(listNodes)-1)]
        dst = src
        while dst == src :
            dst = listNodes[random.randint(0, len(listNodes)-1)]
            
        listDemands.append((src, dst, random.randint(1, bwMax)))
        
    
    return listDemands
        
#Write a list of demands in a file       
def writeInstance(topoName, instanceName, listDemands):
    fileToOpen = os.path.join("..", "instances")
    fileToOpen = os.path.join(fileToOpen, topoName)
    fileToOpen = os.path.join(fileToOpen, "{}.txt".format(instanceName))
    file = open(fileToOpen, 'w')
    
    for demand in listDemands:
        file.write("{},{} {}\n".format(demand[0], demand[1], demand[2]))
    file.close
        


def loadInstance(topoName, instanceName):
    fileToOpen = os.path.join("..", "instances")
    fileToOpen = os.path.join(fileToOpen, topoName)
    fileToOpen = os.path.join(fileToOpen, "{}.txt".format(instanceName))
    file = open(fileToOpen, 'r')
    
    listDemands = []
    
    with open(fileToOpen, "r") as f:
        for line in f :
            line = line.replace("\n","")
            line = line.split(" ")
            bw = int(float(line[1]))
            line = line[0].split(",")
            src = line[0]
            dst = line[1]  
            listDemands.append((src, dst, bw))
    
    file.close
    
    return listDemands