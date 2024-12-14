# coding: utf-8
from __future__ import division # convert int or long division arguments to floating point values before division
from pyomo.environ import *
from pyomo.opt import SolverFactory
import itertools

gd_nodes = ["CORN1", "CORN2"] ##Dispatchables with demand
gn_nodes = [] ##Dispatchables without demand

g_nodes = gd_nodes + gn_nodes 
print ('Gen_Nodes:',len(g_nodes))


model = AbstractModel()


######=================================================########
######               Segment B.1                       ########
######=================================================########

# string indentifiers for the set of generators (in the order of g_nodes list)
model.GD1Gens =  Set()
model.GD2Gens =  Set()

model.Generators = model.GD1Gens | model.GD2Gens
                   
# Generators by fuel-type
model.Gas = Set()
model.Slack = Set()
model.Geothermal = Set()
model.Hydrogen = Set()

# Allocate generators that will ensure minimum reserves
model.ResGenerators = model.Gas | model.Slack | model.Geothermal | model.Hydrogen


######=================================================########
######               Segment B.2                       ########
######=================================================########

### Nodal sets
model.nodes = Set()
model.sources = Set(within=model.nodes)
model.sinks = Set(within=model.nodes)

model.h_nodes = Set()
model.s_nodes = Set()
model.d_nodes = Set()
model.gd_nodes = Set()
model.gn_nodes = Set()
model.td_nodes = Set()
model.tn_nodes = Set()


######=================================================########
######               Segment B.3                       ########
######=================================================########

#####==== Parameters for dispatchable resources ===####

#Generator type
model.typ = Param(model.Generators,within=Any)

#Node name
model.node = Param(model.Generators,within=Any)

#Max capacity
model.maxcap = Param(model.Generators,within=Any)

#Min capacity
model.mincap = Param(model.Generators,within=Any)

#Heat rate
model.heat_rate = Param(model.Generators,within=Any)

#Variable O&M
model.var_om = Param(model.Generators,within=Any)

#Fixed O&M cost
model.fix_om  = Param(model.Generators,within=Any)

#Start cost
model.st_cost = Param(model.Generators,within=Any)

#Ramp rate
model.ramp  = Param(model.Generators,within=Any)

#Minimum up time
model.minup = Param(model.Generators,within=Any)

#Minimum down time
model.mindn = Param(model.Generators,within=Any)

#heat rates and import unit costs
model.gen_cost = Param(model.Generators,within=NonNegativeReals)


######=================================================########
######               Segment B.4                       ########
######=================================================########

######==== Transmission line parameters =======#######
model.linemva = Param(model.sources, model.sinks)
model.linesus = Param(model.sources, model.sinks)

### Transmission Loss as a %discount on production
model.TransLoss = Param(within=NonNegativeReals)

### Maximum line-usage as a percent of line-capacity
model.n1criterion = Param(within=NonNegativeReals)

### Minimum spinning reserve as a percent of total reserve
model.spin_margin = Param(within=NonNegativeReals)

model.m = Param(initialize = 1e5)


######=================================================########
######               Segment B.5                       ########
######=================================================########

######===== Parameters/initial_conditions to run simulation ======####### 
## Full range of time series information
model.SimHours = Param(within=PositiveIntegers)
model.SH_periods = RangeSet(1,model.SimHours+1)
model.SimDays = Param(within=PositiveIntegers)
model.SD_periods = RangeSet(1,model.SimDays+1)

# Operating horizon information 
model.HorizonHours = Param(within=PositiveIntegers)
model.HH_periods = RangeSet(0,model.HorizonHours)
model.hh_periods = RangeSet(1,model.HorizonHours)


######=================================================########
######               Segment B.6                       ########
######=================================================########

#Demand over simulation period
model.SimDemand = Param(model.d_nodes*model.SH_periods, within=NonNegativeReals)
#Horizon demand
model.HorizonDemand = Param(model.d_nodes*model.hh_periods,within=NonNegativeReals,mutable=True)

#Reserve for the entire system
model.SimReserves = Param(model.SH_periods, within=NonNegativeReals)
model.HorizonReserves = Param(model.hh_periods, within=NonNegativeReals,mutable=True)

##Variable resources over simulation period
model.SimHydro = Param(model.h_nodes, model.SH_periods, within=NonNegativeReals)
model.SimSolar = Param(model.s_nodes, model.SH_periods, within=NonNegativeReals)
##model.SimWind = Param(model.w_nodes, model.SH_periods, within=NonNegativeReals)

#Variable resources over horizon
model.HorizonHydro = Param(model.h_nodes,model.hh_periods,within=NonNegativeReals,mutable=True)
model.HorizonSolar = Param(model.s_nodes,model.hh_periods,within=NonNegativeReals,mutable=True)

##Deratef over simulation period 
model.SimDeratef = Param(model.Generators*model.SH_periods, within=NonNegativeReals)

##Horizon Deratef 
model.HorizonDeratef = Param(model.Generators*model.hh_periods,within=NonNegativeReals,mutable=True)

##Initial conditions
model.ini_on = Param(model.Generators, within=NonNegativeReals, mutable=True)
model.ini_mwh = Param(model.Generators, within=NonNegativeReals, mutable=True)


######=================================================########
######               Segment B.7                       ########
######=================================================########

######=======================Decision variables======================########
##Amount of day-ahead energy generated by each generator at each hour
model.mwh = Var(model.Generators,model.HH_periods,within=NonNegativeReals)

model.on = Var(model.Generators,model.HH_periods, within=Binary)

#1 if unit is switching on in hour i, otherwise 0
model.switch = Var(model.Generators,model.HH_periods, within=Binary)

#Amount of spining reserve offered by an unit in each hour
model.srsv = Var(model.Generators,model.HH_periods, within=NonNegativeReals)

#Amount of non-sping reserve offered by an unit in each hour
model.nrsv = Var(model.Generators,model.HH_periods, within=NonNegativeReals)

#dispatch of hydropower from each domestic dam in each hour
model.hydro = Var(model.h_nodes,model.HH_periods,within=NonNegativeReals)

#dispatch of solar-power in each hour
model.solar = Var(model.s_nodes,model.HH_periods,within=NonNegativeReals)

#Voltage angle at each node in each hour
model.vlt_angle = Var(model.nodes,model.HH_periods)


######=================================================########
######               Segment B.8                       ########
######=================================================########

######================Objective function=============########

def SysCost(model):
    fixed = sum(model.maxcap[j]*model.fix_om[j]*model.on[j,i] for i in model.hh_periods for j in model.Generators)
    starts = sum(model.maxcap[j]*model.st_cost[j]*model.switch[j,i] for i in model.hh_periods for j in model.Generators)

    gas = sum(model.mwh[j,i]*(model.heat_rate[j]*model.gen_cost[j] + model.var_om[j]) for i in model.hh_periods for j in model.Gas)
    slack = sum(model.mwh[j,i]*(model.heat_rate[j]*model.gen_cost[j] + model.var_om[j]) for i in model.hh_periods for j in model.Slack)
    geothermal = sum(model.mwh[j,i]*(model.heat_rate[j]*model.gen_cost[j] + model.var_om[j]) for i in model.hh_periods for j in model.Geothermal)
    hydrogen = sum(model.mwh[j,i]*(model.heat_rate[j]*model.gen_cost[j] + model.var_om[j]) for i in model.hh_periods for j in model.Hydrogen)
    
    return fixed + starts + gas + slack + geothermal + hydrogen

model.SystemCost = Objective(rule=SysCost, sense=minimize)


######=================================================########
######               Segment B.9                      ########
######=================================================########

######========== Logical Constraint =========#############
def MwhCon_initial(model,j,i): #v1.3
    if i == 0:
        return (model.mwh[j,i] == model.ini_mwh[j])
    else:
      return Constraint.Skip
model.initial_mwh_constr = Constraint(model.Generators,model.HH_periods, rule=MwhCon_initial)

def OnCon_initial(model,j,i):
    if i == 0:
        return (model.on[j,i] == model.ini_on[j])
    else:
      return Constraint.Skip
model.initial_value_constr = Constraint(model.Generators,model.HH_periods, rule=OnCon_initial)

def SwitchCon2(model,j,i):
    return model.switch[j,i] <= model.on[j,i] * model.m
model.Switch2Constraint = Constraint(model.Generators,model.hh_periods,rule = SwitchCon2)

def SwitchCon3(model,j,i):
    return  model.switch[j,i] <= (1 - model.on[j,i-1]) * model.m  
model.Switch3Constraint = Constraint(model.Generators,model.hh_periods,rule = SwitchCon3)

def SwitchCon4(model,j,i):
    return  model.on[j,i] - model.on[j,i-1] <= model.switch[j,i]
model.Switch4Constraint = Constraint(model.Generators,model.hh_periods,rule = SwitchCon4)


######========== Up/Down Time Constraint =========#############
##Min Up time
def MinUp(model,j,i,k):
    if i > 0 and k > i and k <= min(i+model.minup[j]-1,model.HorizonHours):
        return model.on[j,i] - model.on[j,i-1] <= model.on[j,k]
    else: 
        return Constraint.Skip
model.MinimumUp = Constraint(model.Generators,model.HH_periods,model.HH_periods,rule=MinUp)

##Min Down time
def MinDown(model,j,i,k):
   if i > 0 and k > i and k <= min(i+model.mindn[j]-1,model.HorizonHours):
       return model.on[j,i-1] - model.on[j,i] <= 1 - model.on[j,k]
   else:
       return Constraint.Skip
model.MinimumDown = Constraint(model.Generators,model.HH_periods,model.HH_periods,rule=MinDown)

######==========Ramp Rate Constraints =========#############
def Ramp1(model,j,i):
    a = model.mwh[j,i]
    if i == 1:
        b = model.ini_mwh[j]
    else:
        b = model.mwh[j,i-1]
    return a - b <= model.ramp[j] 
model.RampCon1 = Constraint(model.Generators,model.hh_periods,rule=Ramp1)

def Ramp2(model,j,i):
    a = model.mwh[j,i]
    if i == 1:
        b = model.ini_mwh[j]
    else:
        b = model.mwh[j,i-1]
    return b - a <= model.ramp[j]  
model.RampCon2 = Constraint(model.Generators,model.hh_periods,rule=Ramp2)


######=================================================########
######               Segment B.10                      ########
######=================================================########

######=========== Capacity Constraints ============##########
#Constraints for Max & Min Capacity of dispatchable resources
#derate factor can be below 1 for dry months, otherwise 1
def MaxC(model,j,i):
    return model.mwh[j,i]  <= model.on[j,i] * model.maxcap[j] *model.HorizonDeratef[j,i]
model.MaxCap= Constraint(model.Generators,model.hh_periods,rule=MaxC)

def MinC(model,j,i):
    return model.mwh[j,i] >= model.on[j,i] * model.mincap[j]
model.MinCap= Constraint(model.Generators,model.hh_periods,rule=MinC)

#Max capacity constraints on domestic hydropower 
def HydroC(model,z,i):
    return model.hydro[z,i] <= model.HorizonHydro[z,i]  
model.HydroConstraint= Constraint(model.h_nodes,model.hh_periods,rule=HydroC)

#Max capacity constraints on solar 
def SolarC(model,z,i):
    return model.solar[z,i] <= model.HorizonSolar[z,i]  
model.SolarConstraint= Constraint(model.s_nodes,model.hh_periods,rule=SolarC)


######=================================================########
######               Segment B.11.1                    ########
######=================================================########

#########======================== Power balance in sub-station nodes (with/without demand) ====================#######
###With demand
def TDnodes_Balance(model,z,i):
    demand = model.HorizonDemand[z,i]
    impedance = sum(model.linesus[z,k] * (model.vlt_angle[z,i] - model.vlt_angle[k,i]) for k in model.sinks)   
    return - demand == impedance
model.TDnodes_BalConstraint= Constraint(model.td_nodes,model.hh_periods,rule= TDnodes_Balance)

###Without demand
def TNnodes_Balance(model,z,i):
    #demand = model.HorizonDemand[z,i]
    impedance = sum(model.linesus[z,k] * (model.vlt_angle[z,i] - model.vlt_angle[k,i]) for k in model.sinks)   
    return 0 == impedance
model.TNnodes_BalConstraint= Constraint(model.tn_nodes,model.hh_periods,rule= TNnodes_Balance)


######=================================================########
######               Segment B.11.2                    ########
######=================================================########

######=================== Power balance in nodes of variable resources (without demand in this case) =================########

###Hydropower Plants
def HPnodes_Balance(model,z,i):
    dis_hydro = model.hydro[z,i]
    #demand = model.HorizonDemand[z,i]
    impedance = sum(model.linesus[z,k] * (model.vlt_angle[z,i] - model.vlt_angle[k,i]) for k in model.sinks)
    return (1 - model.TransLoss) * dis_hydro == impedance ##- demand
model.HPnodes_BalConstraint= Constraint(model.h_nodes,model.hh_periods,rule= HPnodes_Balance)


######Solar Plants
def Solarnodes_Balance(model,z,i):
    dis_solar = model.solar[z,i]
    impedance = sum(model.linesus[z,k] * (model.vlt_angle[z,i] - model.vlt_angle[k,i]) for k in model.sinks)
    return (1 - model.TransLoss) * dis_solar == impedance ##- demand
model.Solarnodes_BalConstraint= Constraint(model.s_nodes,model.hh_periods,rule= Solarnodes_Balance)


######=================================================########
######               Segment B.11.3                    ########
######=================================================########

##########============ Power balance in nodes of dispatchable resources with demand ==============############
def GD1_Balance(model,i):
    gd = 1
    thermo = sum(model.mwh[j,i] for j in model.GD1Gens)
    demand = model.HorizonDemand[gd_nodes[gd-1],i]
    impedance = sum(model.linesus[gd_nodes[gd-1],k] * (model.vlt_angle[gd_nodes[gd-1],i] - model.vlt_angle[k,i]) for k in model.sinks)   
    return (1 - model.TransLoss) * thermo - demand == impedance
model.GD1_BalConstraint= Constraint(model.hh_periods,rule= GD1_Balance)

def GD2_Balance(model,i):
    gd = 2
    thermo = sum(model.mwh[j,i] for j in model.GD2Gens)
    demand = model.HorizonDemand[gd_nodes[gd-1],i]
    impedance = sum(model.linesus[gd_nodes[gd-1],k] * (model.vlt_angle[gd_nodes[gd-1],i] - model.vlt_angle[k,i]) for k in model.sinks)   
    return (1 - model.TransLoss) * thermo - demand == impedance
model.GD2_BalConstraint= Constraint(model.hh_periods,rule= GD2_Balance)


######=================================================########
######               Segment B.12                    ########
######=================================================########

######==================Transmission  constraints==================########

####=== Reference Node =====#####
def ref_node(model,i):
    return model.vlt_angle['CORN2',i] == 0
model.Ref_NodeConstraint= Constraint(model.hh_periods,rule= ref_node)


######========== Transmission Capacity Constraints (N-1 Criterion) =========#############
def MaxLine(model,s,k,i):
    if model.linemva[s,k] > 0:
        return (model.n1criterion) * model.linemva[s,k] >= model.linesus[s,k] * (model.vlt_angle[s,i] - model.vlt_angle[k,i])
    else:
        return Constraint.Skip
model.MaxLineConstraint= Constraint(model.sources,model.sinks,model.hh_periods,rule=MaxLine)

def MinLine(model,s,k,i):
    if model.linemva[s,k] > 0:
        return (-model.n1criterion) * model.linemva[s,k] <= model.linesus[s,k] * (model.vlt_angle[s,i] - model.vlt_angle[k,i])
    else:
        return Constraint.Skip
model.MinLineConstraint= Constraint(model.sources,model.sinks,model.hh_periods,rule=MinLine)



######=================================================########
######               Segment B.13                      ########
######=================================================########

######===================Reserve and zero-sum constraints ==================########

##System Reserve Requirement
def SysReserve(model,i):
    return sum(model.srsv[j,i] for j in model.ResGenerators) + sum(model.nrsv[j,i] for j in model.ResGenerators) >= model.HorizonReserves[i]
model.SystemReserve = Constraint(model.hh_periods,rule=SysReserve)

##Spinning Reserve Requirement
def SpinningReq(model,i):
    return sum(model.srsv[j,i] for j in model.ResGenerators) >= model.spin_margin * model.HorizonReserves[i] 
model.SpinReq = Constraint(model.hh_periods,rule=SpinningReq)           

##Spinning reserve can only be offered by units that are online
def SpinningReq2(model,j,i):
    return model.srsv[j,i] <= model.on[j,i]*model.maxcap[j] *model.HorizonDeratef[j,i]
model.SpinReq2= Constraint(model.Generators,model.hh_periods,rule=SpinningReq2) 

##Non-Spinning reserve can only be offered by units that are offline
def NonSpinningReq(model,j,i):
    return model.nrsv[j,i] <= (1 - model.on[j,i])*model.maxcap[j] *model.HorizonDeratef[j,i]
model.NonSpinReq= Constraint(model.Generators,model.hh_periods,rule=NonSpinningReq)


######========== Zero Sum Constraint =========#############
def ZeroSum(model,j,i):
    return model.mwh[j,i] + model.srsv[j,i] + model.nrsv[j,i] <= model.maxcap[j] *model.HorizonDeratef[j,i]
model.ZeroSumConstraint=Constraint(model.Generators,model.hh_periods,rule=ZeroSum)


######======================================#############
######==========        End        =========#############
######=======================================############

