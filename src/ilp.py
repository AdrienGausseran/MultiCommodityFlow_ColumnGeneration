'''
Created on Jun 5, 2021

@author: agausser
'''

import cplex
from cplex.exceptions import CplexSolverError

class MultiCommodityFlowILP(object):
    '''
    classdocs
    '''

    #Create the model
    #    dictLinkUsed is only used when we want to compute the solution on an already used network
    def __init__(self, dictLinks, linksCapacity, listDemands, dictLinksUsed = None):
        self.prob = cplex.Cplex()
        self.prob.parameters.read.datacheck.set(0)
        
        self.prob.objective.set_sense(self.prob.objective.sense.minimize)
        self.prob.set_results_stream(None)
        
        self.listDemands = listDemands
        self.dictLinks = dictLinks
        
        if dictLinksUsed == None:
            dictLinksUsed = {}
        

    
        obj = []        #Objective
        ub = []         #Upper Bound
        rhs = []        #Result for each constraint
        sense = []      #Comparator for each constraint
        colname = []    #Name of the variables
        types = []      #type of the variables
        row = []        #Constraint
        
        #    ---------- ---------- ---------- The Variables
        
        #We create the x variables to know if a link (u,v) is used by a demand
        for i in range(len(listDemands)):
            for u in dictLinks:
                for v in dictLinks[u]:
                    colname.append("x,{},{},{}".format(i,u,v))
                    #obj.append(0)                       #We put the objective at 0 because we will update it every time we solve the problem, because of the two solve functions 
                    obj.append(listDemands[i][2])
                    ub.append(1)
                    types.append('B')
        
        
        #    ---------- ---------- ---------- The Constraints
        
        #Flow conservation constraints
        for i in range(len(listDemands)):
            for u in dictLinks:
                listVar = []
                listVal = []
                for v in dictLinks[u]:
                    #Outgoing link
                    listVar.append("x,{},{},{}".format(i,u,v))
                    listVal.append(1)
                    #Incoming link
                    listVar.append("x,{},{},{}".format(i,v,u))
                    listVal.append(-1)
                row.append([listVar, listVal])
                sense.append('E')
                #If u is the source node
                if (u==listDemands[i][0]):
                    rhs.append(1)
                #If u is the destination
                elif (u==listDemands[i][1]):
                    rhs.append(-1)
                else:
                    rhs.append(0)
                
        
        #Link Capacity constraints
        for u in dictLinks:
            for v in dictLinks[u]:
                listVar = []
                listVal = []
                for i in range(len(listDemands)):
                    listVar.append("x,{},{},{}".format(i,u,v))
                    listVal.append(listDemands[i][2])
                row.append([listVar, listVal])
                sense.append('L')
                base = linksCapacity
                if (u,v) in dictLinksUsed:
                    base -= dictLinksUsed[(u,v)]
                if base < 0:
                    print("ILP pb link capacity {} {} {} {}".format(u,v,linksCapacity,base))
                rhs.append(base)
        
        
        #We add the variables
        self.prob.variables.add(obj=obj, types=types, ub=ub, names=colname)
        #We add the constraints
        self.prob.linear_constraints.add(lin_expr=row, senses=sense, rhs=rhs)
        
        #Set the problem to be an ILP
        self.prob.set_problem_type(1)
        self.prob.parameters.mip.tolerances.mipgap.set(0.000001)
        
        
    #solve the optimization model
    def solve(self, timeLimit, optimalNeeded = True):
        self.prob.parameters.timelimit.set(timeLimit)
        
        """
        #We put the real objective
        numCol = 0
        for i in range(len(self.listDemands)):
            for u in self.dictLinks:
                for v in self.dictLinks[u]:
                    self.prob.objective.set_linear(numCol, self.listDemands[i][2])
                    numCol += 1
        """
        
        #Solving of the problem
        try:
            self.prob.solve()
        except CplexSolverError:
            print("Exception raised during solve")
            return False, {}, {}
    
        # The status can be found at << https://www.ibm.com/docs/en/icos/12.9.0?topic=SSSA5P_12.9.0/ilog.odms.cplex.help/refpythoncplex/html/cplex._internal._subinterfaces.SolutionStatus-class.html >>
        if self.prob.solution.get_status() != 101 and self.prob.solution.get_status() != 102:
            #print("No solution available")
            return False, {}, {}
        
        #TimeLimit
        if optimalNeeded and self.prob.solution.get_status() == 107:
            #print("No solution available")
            return False, {}, {}
        
        if self.prob.solution.get_status() == 107:
            print("     ILP Solution not optimal")
    
        valsVar = self.prob.solution.get_values()
        namesVar = self.prob.variables.get_names()
        
        #print(self.prob.solution.get_objective_value())
        
        return True, namesVar, valsVar
    
    """
    #Solve the decision problem (without the objective)
    def solveDecison(self, timeLimit):
        self.prob.parameters.timelimit.set(timeLimit)
        
        #We put the no objective
        numCol = 0
        for i in range(len(self.listDemands)):
            for u in self.dictLinks:
                for v in self.dictLinks[u]:
                    self.prob.objective.set_linear(numCol, 0)
                    numCol += 1

        #Solving of the problem
        try:
            self.prob.solve()
        except CplexSolverError:
            print("Exception raised during solve")
            return False, {}, {}

    
        # The status can be found at << https://www.ibm.com/docs/en/icos/12.9.0?topic=SSSA5P_12.9.0/ilog.odms.cplex.help/refpythoncplex/html/cplex._internal._subinterfaces.SolutionStatus-class.html >>
        if self.prob.solution.get_status() != 101 and self.prob.solution.get_status() != 102 and self.prob.solution.get_status() != 107:
            print("No solution available")
            return False, {}, {}
        
        
        valsVar = self.prob.solution.get_values()
        namesVar = self.prob.variables.get_names()
        
        return True, namesVar, valsVar
    """    
        
    def terminate(self):
        self.prob.end()
                                            
