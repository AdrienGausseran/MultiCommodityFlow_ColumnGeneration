'''
Created on Jun 5, 2021

@author: agausser
'''

import cplex
from cplex.exceptions import CplexSolverError

class Master(object):
    '''
    classdocs
    '''

    #Create the model
    def __init__(self, dictLinks, linksCapacity, listDemands, firstPaths):
        self.prob = cplex.Cplex()
        #self.prob.parameters.read.datacheck.set(0)
        
        self.prob.objective.set_sense(self.prob.objective.sense.minimize)
        self.prob.set_results_stream(None)
        
        self.listDemands = listDemands
        self.dictLinks = dictLinks
        
        self.nbColumns = len(firstPaths)
        
        self.nbIter = 0
        self.listPaths = []
        for i in range(len(listDemands)):
            self.listPaths.append([firstPaths[i]])

    
        obj = []        #Objective
        ub = []         #Upper Bound
        rhs = []        #Result for each constraint
        sense = []      #Comparator for each constraint
        colname = []    #Name of the variables
        types = []      #type of the variables
        row = []        #Constraint
        numrow = 0
        self.numcol = 0
        
        self.rowOnePath = []
        self.rowLinkCapacity = {}
        
        #    ---------- ---------- ---------- The Variables
        
        #We create the p variables to know if a path is used by a demand
        for i in range(len(listDemands)):
            colname.append("p,{},{}".format(i,0))
            obj.append(len(firstPaths[i][1])*listDemands[i][2])      
            """         ********           ********           ********         """
            """         ********            Advice            ********         """
            """         ********           ********           ********         """
            """    Always put an infinity bound for the master
                   Putting a finite bound may prevent the creation
                   of good columns
                   We put the finite bound just before the ilp optimization
            """
            ub.append(cplex.infinity)
            types.append('C')
            self.numcol += 1
        
        
        #    ---------- ---------- ---------- The Constraints
        
        #One Path per demand constraint
        for i in range(len(listDemands)):
            row.append([["p,{},{}".format(i,0)], [1]])
            sense.append('E')
            rhs.append(1)
            self.rowOnePath.append(numrow)
            numrow +=1
                
        
        #Link Capacity constraints
        for u in dictLinks:
            for v in dictLinks[u]:
                listVar = []
                listVal = []
                for i in range(len(listDemands)):
                    if (u,v) in firstPaths[i][1]:
                        listVar.append("p,{},{}".format(i,0))
                        listVal.append(listDemands[i][2])
                row.append([listVar, listVal])
                sense.append('L')
                rhs.append(linksCapacity)
                self.rowLinkCapacity[(u,v)] = numrow
                numrow +=1
          
        """      
        #We can also write this constraint in standard form ( >= for a minimization) : we have to update addpath in master and update objective in princing
        #Link Capacity constraints
        for u in dictLinks:
            for v in dictLinks[u]:
                listVar = []
                listVal = []
                for i in range(len(listDemands)):
                    if (u,v) in firstPaths[i][1]:
                        listVar.append("p,{},{}".format(i,0))
                        listVal.append(-listDemands[i][2])
                row.append([listVar, listVal])
                sense.append('G')
                rhs.append(-linksCapacity)
                self.rowLinkCapacity[(u,v)] = numrow
                numrow +=1
        """
        
        #We add the variables
        self.prob.variables.add(obj=obj, types=types, ub=ub, names=colname)
        #We add the constraints
        self.prob.linear_constraints.add(lin_expr=row, senses=sense, rhs=rhs)
        
        self.prob.parameters.mip.tolerances.mipgap.set(0.0001)
        
        
    #solve the relaxed model
    def solveFrac(self):
        
        #Set the problem to be a LP
        self.prob.set_problem_type(0)
        self.nbIter += 1
        
        #Solving of the problem
        self.prob.solve()
        
        #Optimal Infeasible
        #In some problem some times we can get "Optimal Infeasible", in this case it's better to re-run the model
        # The status can be found at << https://www.ibm.com/docs/en/icos/12.9.0?topic=SSSA5P_12.9.0/ilog.odms.cplex.help/refpythoncplex/html/cplex._internal._subinterfaces.SolutionStatus-class.html >>
        if self.prob.solution.get_status() == 5:
            self.prob.solve()
            if self.prob.solution.get_status() != 1:
                infoError(self.prob.solution.get_status(), 2, self)
                exit()
        elif self.prob.solution.get_status() != 1:
            infoError(self.prob.solution.get_status(), 1, self)
            exit()
        
        
        return self.prob.solution.get_objective_value()   
    
    def getDuals(self):
        duals = self.prob.solution.get_dual_values()
        
        return duals, self.rowOnePath, self.rowLinkCapacity
    
    #solve the optimization model
    def solveOpt(self, timeLimit, optimalNeeded = True):
        
        #We set the timeLimit
        self.prob.parameters.timelimit.set(timeLimit)
        
        #Set the problem to be an ILP
        self.prob.set_problem_type(1)

        #We put the finite bounds on our variables
        for i in range(self.prob.variables.get_num()):
            self.prob.variables.set_upper_bounds(i,1)
            self.prob.variables.set_types(i, 'B')

        
        #Solving of the problem
        try:
            self.prob.solve()
        except CplexSolverError:
            print("Exception raised during solve")
            return False, {}, {}
    
        # The status can be found at << https://www.ibm.com/docs/en/icos/12.9.0?topic=SSSA5P_12.9.0/ilog.odms.cplex.help/refpythoncplex/html/cplex._internal._subinterfaces.SolutionStatus-class.html >>
        if self.prob.solution.get_status() != 101 and self.prob.solution.get_status() != 102:
            #print("No solution available")
            return False, -1
        
        #TimeLimit
        if optimalNeeded and self.prob.solution.get_status() == 107:
            #print("No solution available")
            return False, -1
        
        if self.prob.solution.get_status() == 107:
            print("     ILP Solution not optimal")
    
        obj = self.prob.solution.get_objective_value()
        #self.prob.write("a.lp")
        
        return True, obj
    
    #We add a new path
    #    A path is : (numberOfTheDemand, alloc)
    def addPath(self, path): 
        
        self.nbColumns += 1
        
        #We take the variable number to use it in the constaint
        numPath = self.numcol
        self.numcol += 1

        #We add the variable
        self.prob.variables.add(obj=[len(path[1])*self.listDemands[path[0]][2]], types=['C'], ub=[cplex.infinity], names=["p,{},{}".format(path[0],len(self.listPaths[path[0]]))])
        self.listPaths[path[0]].append(path)
        
        #Updating the constraint for One path taken
        self.prob.linear_constraints.set_coefficients(self.rowOnePath[path[0]], numPath, 1)
        
        #Updating the constraint for links capacity
        for (u,v) in path[1]:
            self.prob.linear_constraints.set_coefficients(self.rowLinkCapacity[(u,v)], numPath, self.listDemands[path[0]][2])
          
        """
        #This can be used if the link capacity constraint in the mater is written in standard form ( >= )  
        #Updating the constraint for links capacity
        for (u,v) in path[1]:
            self.prob.linear_constraints.set_coefficients(self.rowLinkCapacity[(u,v)], numPath, -self.listDemands[path[0]][2])
        """
    
    def getResult(self, verbose):
        

        valsVar = self.prob.solution.get_values()
        namesVar = self.prob.variables.get_names()
        
        alloc = [[] for _ in range(len(self.listDemands))]
        
        for i in range(len(namesVar)) :
            if valsVar[i] > 0.01:
                tmp = namesVar[i].split(",")
                numDemand = int(float(tmp[1]))
                numPath = int(float(tmp[2]))
                alloc[numDemand] = self.listPaths[numDemand][numPath][1]
                
        for i in range(len(self.listDemands)):
            if len(alloc[i]) == 0:
                print("PB alloc {}".format(i))
                
        if verbose :
            print("")
            print("Column Generation all paths used :")
            for i in range(len(self.listDemands)):
                print("    {} {}    {} Columns".format(i, self.listDemands[i], len(self.listPaths[i])))
                for j in range(len(self.listPaths[i])):
                    print("        {} {}".format(j, self.listPaths[i][j]))
                    
            print("Obj Optimized : {} in {} Iterations with {} columns".format(self.prob.solution.get_objective_value(), self.nbIter, self.nbColumns))
    
        return alloc

        
    def terminate(self):
        self.prob.end()
    
                           
def infoError(status, cas, master):
    print("No solution available for the master")
    print("Cas {}".format(cas))
    print("Status : {}".format(status))          
