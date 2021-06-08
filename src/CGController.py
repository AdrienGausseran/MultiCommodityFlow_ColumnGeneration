'''
Created on Jun 5, 2021

@author: agausser
'''

import master
import pricingProblem

import time
from collections import deque

from multiprocessing import Process, Manager
from random import shuffle
from copy import copy


class CGController(object):
    '''
    classdocs
    '''


    def __init__(self, dictLinks, linksCapacity, listDemands, firstAlloc, verbose = False):
        
        self.dictLinks = dictLinks
        self.linksCapacity = linksCapacity
        self.listDemands = listDemands
        self.nbColumns = 0
        self.verbose = verbose
        
        #The stable stop option can be deactivated
        #    This is usefull to speed up on certain circonstances
        #    If the objective of the relax Master don't improve more than 0.1% in "stableCycle" number of iterations
        #    We stop the iteration and solve the ILP master
        self.stableStop = True
        self.stableCycle = 10
        self.oldObj = deque()
        
        #We create the list of first path to give to the master
        #    We use for that a dummy allocation, it can be given by the ilp without objective or by any
        #    algorithm that give that give a valid allocation. It's better to use a fast algorithm for that
        #A path is = (numDemand, listLinksUsed)
        self.paths = []
        for i in range(len(firstAlloc)):
            self.paths.append((i, firstAlloc[i]))
            
        #Creation of the subProblems
        self.subs = []
        for i in range(len(listDemands)):
            self.subs.append(pricingProblem.PricingProblem(dictLinks, listDemands[i], i))
            
        #Creation of the Master
        self.master = master.Master(dictLinks, linksCapacity, listDemands, self.paths)
        
    
    def solve(self, timelimit, maxiteration = 150, numberOfThread = 1):
        
        if numberOfThread > 1:
            return self.solveMultiThread(timelimit, maxiteration, numberOfThread)
        
        self.nbIteration = 0
        opt = False
        tStart = time.time()
        
        """
        #We launch a first time the pricing problems with only their original cost
        #    Each one will give their shortest path
        #    It's not a mandatory step but for some problems it can help the algorithm to start
        for i in range(len(self.listDemands)):
            reduceCost, namesVar, valsVar = self.subs[i].solve()

            alloc = createSingleAlloc(namesVar, valsVar)
            #We first check that this path is not already the same as the first path given
            same = True
            if not len(alloc) == len(self.master.listPaths[i][0][1]):
                same = False
            else:
                for j in range(len(alloc)):
                    if not alloc[j] in self.master.listPaths[i][0][1]:
                        same = False
                        break
            if not same:
                self.nbColumns +=1
                self.master.addPath((i,alloc))"""
        
        while not opt:
            self.nbIteration += 1
            #We solve the relaxed Master Problem
            self.objRelax = self.master.solveFrac()
            
            #We stop the iteration if make more than maxiteration (this can be set to infinity
            #    We also stop the iteration at 80% of the timelimit to let 20% of the time to optimize the ILP master
            #    Note that it's not mandatory to have a timelimit or a maxiteration, the column generation will converge by itself
            if self.nbIteration == maxiteration or (time.time()-tStart) > (timelimit*0.80):
                break
            #We get the dual values of the constraints
            duals, constraintOnePath, constraintLinksCapacity = self.master.getDuals()
            
            #We will count the number of new paths, if it's 0 at the end of the iteration we can stop
            nbNewPaths = 0
            for i in range(len(self.listDemands)):
                verbose = False
                """if i == 3:
                    verbose = True"""
                self.subs[i].updateObjective(duals, constraintOnePath[i], constraintLinksCapacity, verbose)
                reduceCost, namesVar, valsVar = self.subs[i].solve()
    
                if reduceCost < 0:
                    alloc = createSingleAlloc(namesVar, valsVar)
                    nbNewPaths += 1
                    self.nbColumns +=1
                    opt = False
                    self.master.addPath((i,alloc))
            
            if nbNewPaths == 0:
                opt = True
            #The stable stop option can be deactivated
            #    This is usefull to speed up on certain circonstances
            #    If the objective of the relax Master don't improve more than 0.1% in "stableCycle" number of iterations
            #    We stop the iteration and solve the ILP master
            elif self.stableStop :
                self.oldObj.append(self.objRelax)
                if len(self.oldObj) > self.stableCycle:
                    oldObj = self.oldObj.popleft()
                    if (oldObj- self.objRelax)/float(oldObj)*100 < 0.1:
                        opt = True
        
        #We set the timelimit for the optimization
        limit = max(timelimit*0.2, time.time()-tStart)

        allocPossible, obj = self.master.solveOpt(limit, False)
        
        if not allocPossible:
            listAlloc = []
        else:
            listAlloc = self.master.getResult(self.verbose)
        
        #We terminate the Cplex Object of the master and the subs
        self.master.terminate()
        for sub in self.subs:
            sub.terminate()
        
        return allocPossible, listAlloc
    
    
    def solveMultiThread(self, timelimit, maxiteration, nbThreadSub):

        def doYourJobThread(listSub, duals, constraintOnePath, constraintLinksCapacity, listPath):
            for sub in listSub:
                verbose = False
                sub.updateObjective(duals, constraintOnePath[sub.demandNumber], constraintLinksCapacity, verbose)
                reduceCost, namesVar, valsVar = sub.solve()
                if reduceCost < 0:
                    alloc = createSingleAlloc(namesVar, valsVar)
                    listPath[sub.demandNumber] = (i,alloc)
                else:
                    listPath[sub.demandNumber] = None

        tStart = time.time()
        
        #We creates on list for each threads and we share the pricings between the threads
        listSubThread = [[] for i in range(nbThreadSub)]
        listSubTmp = copy(self.subs)
        shuffle(listSubTmp)
        nbSubByHtread = len(listSubTmp)//nbThreadSub
        listManagerSubThread = Manager().list(range(len(self.listDemands)))
        it = 0
        #We fill in the lists
        for i in range(nbSubByHtread):
            for subThread in listSubThread:
                subThread.append(listSubTmp[it])
                listManagerSubThread[listSubTmp[it].demandNumber] = None
                it += 1
        for i in range(len(listSubTmp) % len(listSubThread)):
            listSubThread[i].append(listSubTmp[it])
            listManagerSubThread[listSubTmp[it].demandNumber] = None
            it += 1
        
        opt = False
        while not opt:
            self.nbIteration += 1
            #We solve the relaxed Master Problem
            self.objRelax = self.master.solveFrac()
            
            #We stop the iteration if make more than maxiteration (this can be set to infinity
            #    We also stop the iteration at 80% of the timelimit to let 20% of the time to optimize the ILP master
            #    Note that it's not mandatory to have a timelimit or a maxiteration, the column generation will converge by itself
            if self.nbIteration == maxiteration or (time.time()-tStart) > (timelimit*0.80):
                break
            #We get the dual values of the constraints
            duals, constraintOnePath, constraintLinksCapacity = self.master.getDuals()
            
            #We will count the number of new paths, if it's 0 at the end of the iteration we can stop
            nbNewPaths = 0
            #We launch all the threads
            listProcess = []
            for listSub in listSubThread:
                p = Process(target=doYourJobThread, args=(listSub, duals, constraintOnePath, constraintLinksCapacity, listManagerSubThread))
                p.start()
                listProcess.append(p)
            #We wait for the ends of the threads
            for p in listProcess:
                p.join()
            #We add the new paths
            for sub in self.subs:
                path = listManagerSubThread[sub.demandNumber]
                if not path == None :
                    nbNewPaths += 1
                    opt = False
                    self.nbColumns += 1
                    self.master.addPath(path)
            
            for p in listProcess:
                p.terminate()
            
            if nbNewPaths == 0:
                opt = True
            #The stable stop option can be deactivated
            #    This is usefull to speed up on certain circonstances
            #    If the objective of the relax Master don't improve more than 0.1% in "stableCycle" number of iterations
            #    We stop the iteration and solve the ILP master
            elif self.stableStop :
                self.oldObj.append(self.objRelax)
                if len(self.oldObj) > self.stableCycle:
                    oldObj = self.oldObj.popleft()
                    if (oldObj- self.objRelax)/float(oldObj)*100 < 0.1:
                        opt = True
                
        
        #We set the timelimit for the optimization
        limit = max(timelimit*0.2, time.time()-tStart)

        allocPossible, obj = self.master.solveOpt(limit, False)
        
        if not allocPossible:
            listAlloc = []
        else:
            listAlloc = self.master.getResult(self.verbose)
        
        #We terminate the Cplex Object of the master and the subs
        self.master.terminate()
        for sub in self.subs:
            sub.terminate()
        
        return allocPossible, listAlloc
        
                
        
def createSingleAlloc(namesVar, valsVar):
    alloc = []

    #We start at one because the variable 0 is dualOnePath
    for i in range(1, len(namesVar)) :
        if valsVar[i] > 0.01:
            tmp = namesVar[i].split(",")
            num = int(float(tmp[1]))
            u = tmp[2]
            v = tmp[3]
            alloc.append((u,v))
            
    
    return alloc