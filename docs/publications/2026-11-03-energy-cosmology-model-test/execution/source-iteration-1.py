# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation and numerical analysis: OpenAI Codex.
"""Bounded, reproducible FLRW model experiment; Python standard library only.

This is a numerical representation of an assumed Lorentzian metric, not a
physical observation, a claim of internal spacetime emergence, or a novel law.
Normalized units: c=G=H_reference=k_B=1. Parameters are illustrative, not a fit.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

RHO_CRIT = 3.0 / (8.0 * math.pi)


@dataclass(frozen=True)
class Model:
    name: str
    omega_m: float
    omega_r: float
    omega_v: float

    @property
    def curvature(self):
        return self.omega_m + self.omega_r + self.omega_v - 1.0

    @property
    def length(self):
        return 1.0 / math.sqrt(self.curvature) if self.curvature > 1e-12 else 1.0

    @property
    def reference_volume(self):
        # The full proper volume of S^3 only for the positively curved model.
        return 2.0 * math.pi**2 * self.length**3 if self.curvature > 1e-12 else 1.0

    def initial(self):
        return [1.0, 1.0, RHO_CRIT*self.omega_m, RHO_CRIT*self.omega_r,
                RHO_CRIT*self.omega_v, 0.0, 10.0, 0.0]


def rhs(model, y, *, wrong_photon_sign=False):
    a, velocity, rm, rr, rv, chi, photon, work = y
    if a <= 0 or any(not math.isfinite(x) for x in y):
        raise ValueError("nonpositive scale factor or nonfinite state")
    hubble = velocity / a
    pressure = rr / 3.0 - rv
    acceleration = -(4.0*math.pi/3.0) * a * (rm + 2.0*rr - 2.0*rv)
    volume_rate = 3.0 * model.reference_volume * a*a*velocity
    return [velocity, acceleration, -3.0*hubble*rm, -4.0*hubble*rr, 0.0,
            1.0/(a*model.length), (1.0 if wrong_photon_sign else -1.0)*hubble*photon,
            -pressure*volume_rate]


def rk4_step(function, y, h):
    def shifted(v, k, factor):
        return [a+factor*b for a,b in zip(v,k)]
    k1 = function(y)
    k2 = function(shifted(y,k1,h/2.0))
    k3 = function(shifted(y,k2,h/2.0))
    k4 = function(shifted(y,k3,h))
    return [a+h*(b+2*c+2*d+e)/6.0 for a,b,c,d,e in zip(y,k1,k2,k3,k4)]


def integrate(model, steps, *, clock_scale=1.0, wrong_photon_sign=False):
    if steps < 4 or clock_scale <= 0:
        raise ValueError("invalid integration settings")
    y = model.initial()
    rows = [(0.0,y[:])]
    # coordinate lambda = clock_scale * proper time; endpoint proper time is 1.
    h = clock_scale/steps
    f = lambda q: [v/clock_scale for v in rhs(model,q,wrong_photon_sign=wrong_photon_sign)]
    for j in range(steps):
        y = rk4_step(f,y,h)
        rows.append(((j+1)/steps,y[:]))
    return rows


def relative(a,b):
    return abs(a-b)/max(abs(a),abs(b),1e-30)


def diagnose(model, rows):
    initial = model.initial()
    v0 = model.reference_volume
    e0 = v0*sum(initial[2:5])
    worst = dict.fromkeys(["friedmann","matter_scaling","radiation_scaling",
                           "work_balance","photon_redshift","conditional_bit_ceiling"],0.0)
    initial_ceiling = 0.5*initial[6]/math.log(2.0)
    for time,y in rows:
        a,velocity,rm,rr,rv,chi,photon,work = y
        hubble = velocity/a
        expected_h2 = 8.0*math.pi*(rm+rr+rv)/3.0-model.curvature/(a*a)
        energy = v0*a**3*(rm+rr+rv)
        values = {"friedmann": relative(hubble*hubble,expected_h2),
                  "work_balance": abs(energy-e0-work)/max(abs(energy),abs(e0),abs(work),1e-30),
                  "photon_redshift": relative(photon*a,initial[6]),
                  "conditional_bit_ceiling": relative(0.5*photon/(math.log(2.0)/a),initial_ceiling)}
        if initial[2]: values["matter_scaling"] = relative(rm*a**3,initial[2])
        if initial[3]: values["radiation_scaling"] = relative(rr*a**4,initial[3])
        for key,value in values.items(): worst[key] = max(worst[key],value)
    a,v,rm,rr,rv,chi,photon,work = rows[-1][1]
    return {"maximum_relative_residuals":worst,"final":{
        "proper_time":rows[-1][0],"a":a,"H":v/a,"full_or_cell_volume":v0*a**3,
        "matter_energy":v0*a**3*rm,"radiation_energy":v0*a**3*rr,
        "vacuum_energy":v0*a**3*rv,"material_total":v0*a**3*(rm+rr+rv),
        "material_total_initial":e0,"integrated_minus_p_dV":work,
        "radial_null_coordinate":chi,"photon_energy":photon,
        "redshift_from_a1":a-1.0,"temperature_reference_over_a":1.0/a,
        "conditional_bit_ceiling_eta_half":0.5*photon/(math.log(2.0)/a),
        "radial_metric_determinant":-(a*model.length)**2}}


def first_order_a(model,steps):
    # Independent formulation uses the first Friedmann equation and analytic
    # fluid dilution, rather than evolving acceleration and densities.
    def derivative(q):
        a=q[0]
        return [a*math.sqrt(model.omega_m/a**3+model.omega_r/a**4+model.omega_v-model.curvature/a**2)]
    y=[1.0]
    for _ in range(steps): y=rk4_step(derivative,y,1.0/steps)
    return y[0]


def main(out):
    out.mkdir(parents=True,exist_ok=True)
    models=[Model("flat_dust",1,0,0),Model("flat_radiation",0,1,0),
            Model("flat_vacuum",0,0,1),Model("closed_mixed",0.3,0.0001,0.7999)]
    checks=[]
    def check(name,condition,**evidence):
        checks.append({"name":name,"passed":bool(condition),**evidence})
    cases={}
    for model in models:
        rows=integrate(model,800)
        result=diagnose(model,rows)
        result["parameters"]=asdict(model)
        result["curvature"]=model.curvature
        result["volume_scope"]="entire compact S3 spatial slice, material energy only" if model.curvature>1e-12 else "finite fiducial cell in spatially flat model"
        cases[model.name]=result
        for key,val in result["maximum_relative_residuals"].items():
            check(model.name+":"+key,val<2e-9,residual=val,tolerance=2e-9)
        a=result["final"]["a"]
        expected={"flat_dust":2.5**(2.0/3.0),"flat_radiation":math.sqrt(3.0),"flat_vacuum":math.e}.get(model.name)
        if expected is not None:
            error=relative(a,expected);check(model.name+":analytic_solution",error<2e-10,residual=error)
        independent=first_order_a(model,800)
        check(model.name+":two_ODE_formulations",relative(a,independent)<2e-10,
              relative_difference=relative(a,independent))
        transformed=integrate(model,800,clock_scale=3.0)[-1][1]
        difference=max(relative(x,y) for x,y in zip(rows[-1][1],transformed) if x or y)
        check(model.name+":time_coordinate_change",difference<2e-11,relative_difference=difference)
        if model.name=="closed_mixed":
            with (out/"closed_mixed_trajectory.csv").open("w",newline="") as f:
                writer=csv.writer(f);writer.writerow(["proper_time","a","a_dot","rho_m","rho_r","rho_v","chi_null","photon_energy","integrated_minus_p_dV"])
                for time,y in rows:writer.writerow([format(z,".17g") for z in [time,*y]])
            # Curvature computed from finite differences of recorded geometry.
            ricci_errors=[]
            for j in range(1,len(rows)-1):
                a,vel,rm,rr,rv,*_=rows[j][1]
                a_ddot=(rows[j+1][1][0]-2*a+rows[j-1][1][0])/(1/800)**2
                geometric=6*(a_ddot/a+(vel/a)**2+model.curvature/a**2)
                stress=8*math.pi*(rm+4*rv)
                ricci_errors.append(relative(geometric,stress))
            check("closed_mixed:geometry_stress_Ricci",max(ricci_errors)<2e-6,
                  max_relative_difference=max(ricci_errors),method="central finite difference of a(t)")
    # Fourth-order convergence against exact dust solution, before roundoff.
    dust=models[0];convergence=[]
    for n in [25,50,100,200]:
        a=integrate(dust,n)[-1][1][0]
        convergence.append({"steps":n,"absolute_error":abs(a-2.5**(2.0/3.0))})
    ratios=[convergence[j]["absolute_error"]/convergence[j+1]["absolute_error"] for j in range(3)]
    check("RK4:step_halving",all(10<r<25 for r in ratios),error_ratios=ratios)
    bad=diagnose(models[-1],integrate(models[-1],800,wrong_photon_sign=True))
    bad_error=bad["maximum_relative_residuals"]["photon_redshift"]
    check("negative_control:wrong_photon_sign_detected",bad_error>0.1,residual=bad_error)
    closed=cases["closed_mixed"]["final"]
    change=closed["material_total"]/closed["material_total_initial"]
    check("negative_control:constant_material_energy_rejected",abs(change-1)>0.1,final_over_initial=change)
    check("counterexample:rest_mass_is_not_photon_momentum",1.0!=0.0,m=1,c=1,p=0,mc2=1,pc=0)
    # Satisfiability by definitions is separately labelled, never a new law.
    param_cases=[]
    for energy in [0.125,1.0,7.0,100.0]:
        c,kTln2,G,m1,m2=2.0,3.0,5.0,7.0,11.0
        meq,p,I,r=energy/c**2,energy/c,energy/kTln2,G*m1*m2/energy
        terms=[energy,meq*c**2,p*c,kTln2*I,G*m1*m2/r]
        error=max(relative(x,energy) for x in terms)
        check("constructed_parameterization:E="+str(energy),error<1e-14,max_relative_residual=error)
        param_cases.append({"E":energy,"m_energy_equivalent":meq,"p_massless_carrier":p,
                            "I_idealized_erased_entropy_bits":I,"r_defined_from_E":r,
                            "meaning":"definitions for distinct quantities; not one particle's invariant mass"})
    result={"schema":"qikvrt-cosmology-model-experiment/v1","status":"PASS" if all(c["passed"] for c in checks) else "FAIL",
            "evidence_class":"NUMERICAL_MODEL_TEST","scientific_novelty":"NOT_ESTABLISHED",
            "physical_measurement":False,"internal_spacetime_emergence_demonstrated":False,
            "universal_poster_identity_proved":False,"original_metric":"assumed FLRW, not derived from information",
            "units":"c=G=H_reference=k_B=1; all parameters illustrative",
            "duration_proper_time":1.0,"default_steps":800,"cases":cases,
            "checks":checks,"convergence":convergence,"constructed_equalities":param_cases,
            "scope":"Closed model permits full proper-volume material-energy integral; no observer-independent gravitational total assigned.",
            "conditional_information_bound":"eta*E_packet/(k_B*T*ln2), assuming usable work eta*E_packet; no erasure device simulated",
            "checker_independence":"analytic solutions and two formulations share GR/FLRW assumptions; not independent physical observations",
            "runtime":{"python":sys.version,"implementation":platform.python_implementation()},
            "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/"RESULTS.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"status":result["status"],"passed":sum(c["passed"] for c in checks),"total":len(checks),
                      "failed":[c for c in checks if not c["passed"]],"closed_model_final":closed,
                      "convergence_ratios":ratios},indent=2))
    return 0 if result["status"]=="PASS" else 1


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,default=Path(__file__).parent/"results")
    raise SystemExit(main(parser.parse_args().output))
