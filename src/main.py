'''
Created on Jun 5, 2021

@author: agausser
'''

import instanceLoader
import ilp
import CGController
import time


#Creation of an allocation for a list of demands using the name of the variables and their value from the ILP
#    An alloc is simply the list of the links used by a demand
#    Alloc[i] correspond to the allocation of listDemands[i]
def createAlloc(namesVar, valsVar, listDemands):
    
    alloc = [[] for _ in range(len(listDemands))]

    for i in range(len(namesVar)) :
        if valsVar[i] > 0.01:
            tmp = namesVar[i].split(",")
            num = int(float(tmp[1]))
            u = tmp[2]
            v = tmp[3]
            alloc[num].append((u,v))
            
    for i in range(len(listDemands)):
        if len(alloc[i]) == 0:
            print("PB alloc {}".format(i))
    
    return alloc

#Creation of an allocation for a single demand using the name of the variables and their value from the ILP
#    An alloc is simply the list of the links used by a demand
def createSingleAlloc(namesVar, valsVar):
    alloc = []

    for i in range(len(namesVar)) :
        if valsVar[i] > 0.01:
            tmp = namesVar[i].split(",")
            num = int(float(tmp[1]))
            u = tmp[2]
            v = tmp[3]
            alloc.append((u,v))

    return alloc

#Update the link usage    Used only when we want to alloc the demands one by one
#    linkUsed is a dictionary of link and if a link is inside, the value correspond to the usage of the link
#    alloc and demand correspond to the new alloc for a single demand to take into account
def updateLinkUsage(linksUsed, alloc, demand):
    for (u,v) in alloc:
        if not (u,v) in linksUsed:
            linksUsed[(u,v)] = 0
        linksUsed[(u,v)] += demand[2]


#Compute the objective value of a list of demands        
def objective(alloc, listDemands):
    obj = 0
    for i in range(len(listDemands)):
        obj += len(alloc[i])*listDemands[i][2]
    return obj


#Verify the validity of an allocation
def verifyAlloc(alloc, listDemands, linksCapacity):
    
    #We verify the flow conservation
    for i in range(len(listDemands)):
        src = listDemands[i][0]
        for _ in range(len(alloc[i])):
            for j in range(len(alloc[i])):
                if alloc[i][j][0] == src:
                    src = alloc[i][j][1]

        if  not src == listDemands[i][1]:
            print("Bad Allocation : flow conservation not respected : {}    {}".format(listDemands[i], alloc[i]))

            
    #We verify the links capacity
    linkUsage = {}
    for i in range(len(listDemands)):
        updateLinkUsage(linksUsed, alloc[i], listDemands[i])
    for l in linkUsage:
        if linkUsage[l] > linksCapacity:
            print("Bad Allocation : link {} is over provision : {} / {}".format(l, linkUsage[l], linksCapacity))





"""    ********************************************************************************************    """
"""                                                Main                                                """
"""    ********************************************************************************************    """

if __name__ == '__main__':
    
    topoName = "ta2"
    instanceName = "instance1"    
    
    #There are 100 demands for instance1, 1000 for instance2 and 5000 for instance3
    dictLinkCapacity = { "ta1" : { "instance1" : 18, "instance2" : 150, "instance3" : 800}, "ta2" : {"instance1" : 18,"instance2" : 200, "instance3" : 800}}
    
    #If load == False : we create a new instance
    load = True
    
    # Loading of the topology
    dictLinks = instanceLoader.loadTopo(topoName)   
    
    """for u in dictLinks:
        for v in dictLinks[u]:
            print("{},{}".format(u,v))"""
    
    #Creation of a new instance
    if not load :
        nbDemands = 20
        listDemands = instanceLoader.createInstance(dictLinks, nbDemands)
        instanceLoader.writeInstance(topoName, instanceName, listDemands)
        print("Instance created")
    
    #Loading of an existing instance
    else:
        #Loading of the instance
        listDemands = instanceLoader.loadInstance(topoName, instanceName)
        linksCapacity = dictLinkCapacity[topoName][instanceName]
        
        """    ********************************************************************************************    """
        """                                        Dummy Allocation                                            """
        """    ********************************************************************************************    """
        """    The dummy allocation is just a valid allocation
               It's not made to be optimal, it's only made to be used
               as a first allocation by the Column Generarion.
               Multiple techniques can be used : 
                   - Allocate the demand one by one (Used here)
                   - Using the ILP without the objective (we need to add constraint to stop cycle)
                   - Using a greedy algorithm (fastest and best solution)
        """
        
        
        allocDummy = []
        linksUsed = {}
        
        t = time.time()
        #We iteratively allocate each demand
        #Not the best and fastest way to do it but the fastest to implement
        for i in range(len(listDemands)):
            solverIlp = ilp.MultiCommodityFlowILP(dictLinks, linksCapacity, [listDemands[i]], linksUsed)
            allocPossible, namesVar, valsVar = solverIlp.solve(1)
            if allocPossible:
                alloc = createSingleAlloc(namesVar, valsVar)
                allocDummy.append(alloc)
                updateLinkUsage(linksUsed, alloc, listDemands[i])
            else:
                break
        t = time.time()-t
        
        if allocPossible:
            #print(allocDummy)
            print("Dummy allocation, Objective = {} in {} seconds".format(objective(allocDummy, listDemands), round(t,2)))
            verifyAlloc(allocDummy, listDemands, linksCapacity)
        else: 
            print("Dummy allocation IMPOSSIBLE")
            exit()






        """    ********************************************************************************************    """
        """                                          ILP Allocation                                            """
        """    ********************************************************************************************    """
        """    The ILP allocation give the optimal allocation
               It's made to be compare with the Column generation and the dummy one
               In some problem this allocation will take wayyyyy more time than the CG one
               On This problem the ILP is faster than the CG one
               By changing the objective we may make the problem harder for the ILP :
                   By minimizing the number of links activated for example
        """

        solverIlp = ilp.MultiCommodityFlowILP(dictLinks, linksCapacity, listDemands)
        t = time.time()
        allocPossible, namesVar, valsVar = solverIlp.solve(100)
        t = time.time()-t
        
        if allocPossible:
            alloc = createAlloc(namesVar, valsVar, listDemands)
            #print(alloc)
            print("ILP allocation, Objective = {} in {} seconds".format(objective(alloc, listDemands), round(t,2)))
            verifyAlloc(alloc, listDemands, linksCapacity)
            """for i in range(len(listDemands)):
                print("{}    {}".format(listDemands[i], alloc[i]))"""
        else: 
            print("ILP allocation IMPOSSIBLE")
            
            
            
            
            
        """    ********************************************************************************************    """
        """                                           CG Allocation                                            """
        """    ********************************************************************************************    """
        """    To compute the allocation we need a master problem and a set of pricing problem
               CGController controls the CG algorithm
               On This problem the ILP is faster than the CG one
               By changing the objective we may make the problem harder for the ILP :
                   By minimizing the number of links activated for example
        """
        #Number of threads used to manage the pricing problems (not Cplex itself)
        #By changing the number of threads we may speed up the process on certain problems
        #but we may also change the final solution and its objective
        #    The problem and the size of it must be consider, as well as the CPU you're using
        numberOfThread = 1
            
        solverCG = CGController.CGController(dictLinks, linksCapacity, listDemands, allocDummy)
        t = time.time()
        allocPossible, alloc = solverCG.solve(100,numberOfThread)
        t = time.time()-t
        
        if allocPossible:
            #print(alloc)
            print("CG allocation, Objective = {} in {} seconds".format(objective(alloc, listDemands), round(t,2)))
            verifyAlloc(alloc, listDemands, linksCapacity)

        else: 
            print("CG allocation IMPOSSIBLE")
        