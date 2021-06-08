'''
Created on Jun 5, 2021

@author: agausser
'''

import cplex
from cplex.exceptions import CplexSolverError

class PricingProblem(object):
    '''
    classdocs
    '''

    #Create the model
    def __init__(self, dictLinks, demand, demandNumber):
        self.prob = cplex.Cplex()
        self.prob.parameters.read.datacheck.set(0)
        
        self.prob.objective.set_sense(self.prob.objective.sense.minimize)
        self.prob.set_results_stream(None)
        
        self.dictLinks = dictLinks
        self.demand = demand
        self.demandNumber = demandNumber
        

    
        obj = []        #Objective
        ub = []         #Upper Bound
        rhs = []        #Result for each constraint
        sense = []      #Comparator for each constraint
        colname = []    #Name of the variables
        types = []      #type of the variables
        row = []        #Constraint
              
        
        
        #Variable only used for the objective : update by the dual
        colname.append("dualOnePath")
        obj.append(0)
        ub.append(1)
        types.append("B")
        row.append([["dualOnePath"], [1]])
        sense.append('E')
        rhs.append(1)
        
        
        
        #    ---------- ---------- ---------- The Variables
        
        #We create the x variables to know if a link (u,v) is used by a demand
        for u in dictLinks:
            for v in dictLinks[u]:
                colname.append("x,{},{},{}".format(0,u,v))
                obj.append(demand[2])                       
                ub.append(1)
                types.append('B')
        
        
        #    ---------- ---------- ---------- The Constraints
        
        #Flow conservation constraints
        for u in dictLinks:
            listVar = []
            listVal = []
            for v in dictLinks[u]:
                #Outgoing link
                listVar.append("x,{},{},{}".format(0,u,v))
                listVal.append(1)
                #Incoming link
                listVar.append("x,{},{},{}".format(0,v,u))
                listVal.append(-1)
            row.append([listVar, listVal])
            sense.append('E')
            #If u is the source node
            if (u==demand[0]):
                rhs.append(1)
            #If u is the destination
            elif (u==demand[1]):
                rhs.append(-1)
            else:
                rhs.append(0)
                
        
        
        #We add the variables
        self.prob.variables.add(obj=obj, types=types, ub=ub, names=colname)
        #We add the constraints
        self.prob.linear_constraints.add(lin_expr=row, senses=sense, rhs=rhs)
        
        #Set the problem to be an ILP
        self.prob.set_problem_type(1)
        self.prob.parameters.mip.tolerances.mipgap.set(0.0001)
        
        
    #solve the optimization model
    def solve(self, optimalNeeded = True):
        
        
        #Solving of the problem
        try:
            self.prob.solve()
        except CplexSolverError:
            print("Exception raised during solve")
            return 1, {}, {}
    
        # The status can be found at << https://www.ibm.com/docs/en/icos/12.9.0?topic=SSSA5P_12.9.0/ilog.odms.cplex.help/refpythoncplex/html/cplex._internal._subinterfaces.SolutionStatus-class.html >>
        if self.prob.solution.get_status() != 101 and self.prob.solution.get_status() != 102:
            #print("No solution available")
            return 1, {}, {}
        
        #TimeLimit
        if optimalNeeded and self.prob.solution.get_status() == 107:
            #print("No solution available")
            return 1, {}, {}
        
    
        valsVar = self.prob.solution.get_values()
        namesVar = self.prob.variables.get_names()
        
        #It's important to round the objective
        #    In some problems if we don't round the objective we can miss good columns
        obj = round(self.prob.solution.get_objective_value(),6)
        
        return obj, namesVar, valsVar
    
    def updateObjective(self, duals, rowOnePath, rowLinkCapacity, verbose):
        if verbose:
            print("")
            print("Update objective of {}".format(self.demand))
            
        #We update the objective with the dual value of the one path constraint.
        #    The variable used is "dualOnePath" it's the first variable so it's position is 0
        dual = duals[rowOnePath]
        self.prob.objective.set_linear(0, -dual)
        if verbose:
            print("    onePath {}".format(-dual))
        
        #We update the objective with the dual value of the links capacity constraints.
        #    The variables used are the "x", range from 1 to len(variables)-1
        numcol = 1
        for u in self.dictLinks:
            for v in self.dictLinks[u]:
                dual = duals[rowLinkCapacity[(u,v)]]
                self.prob.objective.set_linear(numcol, self.demand[2] - dual * self.demand[2])
                if verbose:
                    print("    link {},{} {}    {}".format(u,v, self.demand[2] - dual * self.demand[2], dual))
                numcol += 1
        
             
        """     
        #This can be used if the link capacity constraint in the mater is written in standard form ( >= )
        #We update the objective with the dual value of the links capacity constraints.
        #    The variables used are the "x", range from 1 to len(variables)-1
        numcol = 1
        for u in self.dictLinks:
            for v in self.dictLinks[u]:
                dual = duals[rowLinkCapacity[(u,v)]]
                #print("DualLink : {}".format(dual))

                self.prob.objective.set_linear(numcol, self.demand[2] + dual * self.demand[2])
                if verbose:
                    print("    link {},{} {}    {}".format(u,v, self.demand[2] + dual * self.demand[2], dual))
                numcol += 1

                
        """
    
        
    def terminate(self):
        self.prob.end()
    
                                            
