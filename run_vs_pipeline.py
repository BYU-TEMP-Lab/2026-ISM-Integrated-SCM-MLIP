import os
import re
import argparse
import numpy as np
from ase import units
from ase.build import bulk
from ase.md.langevin import Langevin
from ase.md.bussi import Bussi
from ase.md.verlet import VelocityVerlet
from mace.calculators import MACECalculator
from ase.md.velocitydistribution import MaxwellBoltzmannDistribution, Stationary
from ase.optimize import FIRE
from ase.data import atomic_masses, atomic_numbers

# =========================================================
# SYSTEM PARAMETERS & AUTO-SCALING LOGIC
# =========================================================
MONOVALENT = ['Li', 'Na', 'K', 'Rb', 'Cs']
DIVALENT = ['Mg', 'Ca', 'Sr', 'Ba', 'Zn']
TETRAVALENT = ['Zr']

def parse_composition_and_scale(comp_str):
    """Parses standard composition strings and dynamically scales to the best lattice."""
    components = comp_str.split('-')
    num_components = len(components) # Count the number of salts
    
    fractions = {}
    has_cs = False
    has_divalent = False
    
    for comp in components:
        match = re.match(r"([0-9.]+)([A-Z][a-z]?)(Cl\d?)", comp)
        if not match:
            raise ValueError(f"Invalid format: {comp}. Must be like '0.417NaCl'.")
            
        frac = float(match.group(1))
        cation = match.group(2)
        fractions[cation] = frac
        
        if cation == 'Cs':
            has_cs = True
        if cation in DIVALENT:
            has_divalent = True
        
    tot_frac = sum(fractions.values())
    fractions = {k: v / tot_frac for k, v in fractions.items()}
    
    # DYNAMIC SCALING LOGIC
    if has_divalent or 'Zr' in fractions:
        structure_type = 'fluorite'
        supercell_dim = 8 if num_components >= 4 else 3
        total_cation_sites = 4 * (supercell_dim ** 3) # 4 cations per unit cell
    elif has_cs:
        structure_type = 'cesiumchloride'
        # assuming the only time Cs is in the salt will be when the huge salts are being simulated
        supercell_dim = 11 if num_components >= 4 else 5 
        total_cation_sites = 1 * (supercell_dim ** 3)
    else:
        structure_type = 'rocksalt'
        supercell_dim = 4 if num_components >= 4 else 3
        total_cation_sites = 4 * (supercell_dim ** 3) # 4 cations per unit cell
        
    atom_counts = {k: int(round(v * total_cation_sites)) for k, v in fractions.items()}
    
    diff = total_cation_sites - sum(atom_counts.values())
    if diff != 0:
        largest_cation = max(fractions, key=fractions.get)
        atom_counts[largest_cation] += diff
        
    n_cl = 0
    for cation, count in atom_counts.items():
        if cation in TETRAVALENT:
            n_cl += count * 4
        elif cation in DIVALENT:
            n_cl += count * 2
        elif cation in MONOVALENT:
            n_cl += count * 1
            
    atom_counts['Cl'] = n_cl
    
    # Return the new supercell_dim variable so the main script can use it!
    return atom_counts, structure_type, supercell_dim

def main():
    parser = argparse.ArgumentParser(description="Universal MACE Speed of Sound Calculator")
    parser.add_argument('--comp', type=str, required=True, help='Composition e.g., "0.5NaCl-0.5KCl"')
    parser.add_argument('--temp', type=float, required=True, help='Target Temperature in K')
    parser.add_argument('--density', type=float, required=True, help='Initial density guess in g/cm^3')
    parser.add_argument('--seed', type=int, required=True, help='Random seed for thermal velocities')
    parser.add_argument('--model', type=str, default='SuperSalt-swa.model', help='Path to MACE model')
    args = parser.parse_args()

    atom_counts, structure_type, supercell_dim = parse_composition_and_scale(args.comp)
    elements = list(atom_counts.keys())
    sys_cations = [el for el in elements if el != 'Cl']
    total_atoms = sum(atom_counts.values())
    
    TARGET_TEMP = args.temp
    SYSTEM_NAME = args.comp.replace('.', '')
    RANDOM_SEED = args.seed

    print("# =========================================================")
    print(f"# INITIALIZING {SYSTEM_NAME} Vs ARRAY (SEED {RANDOM_SEED})")
    print("# =========================================================")
    print(f"Target Temp: {TARGET_TEMP} K | Density: {args.density} g/cm^3")
    print(f"Structure Base: {structure_type.capitalize()} | Total Atoms: {total_atoms}")

    # =========================================================
    # 1. SETUP & BUILD (CONFIGURATIONAL SEED = 42)
    # =========================================================
    # HARDCODED seed so the physical lattice is identical for all array tasks
    np.random.seed(42)

    calc = MACECalculator(model_paths=args.model, device='cuda')

    if structure_type == 'cesiumchloride':
        atoms = bulk('CsCl', crystalstructure='cesiumchloride', a=4.12, cubic=True)
        atoms = atoms * (supercell_dim, supercell_dim, supercell_dim)
        base_cation_symbol = 'Cs'
        base_anion_symbol = 'Cl'
    elif structure_type == 'fluorite':
        atoms = bulk('CaF2', crystalstructure='fluorite', a=5.46, cubic=True)
        atoms = atoms * (supercell_dim, supercell_dim, supercell_dim)
        base_cation_symbol = 'Ca'
        base_anion_symbol = 'F'
    else:
        atoms = bulk('NaCl', crystalstructure='rocksalt', a=5.64, cubic=True)
        atoms = atoms * (supercell_dim, supercell_dim, supercell_dim)
        base_cation_symbol = 'Na'
        base_anion_symbol = 'Cl'

    base_cat_indices = [atom.index for atom in atoms if atom.symbol == base_cation_symbol]
    base_an_indices = [atom.index for atom in atoms if atom.symbol == base_anion_symbol]

    np.random.shuffle(base_cat_indices)
    
    current_idx = 0
    for cation in sys_cations:
        count = atom_counts[cation]
        indices = base_cat_indices[current_idx : current_idx + count]
        for i in indices: atoms[i].symbol = cation
        current_idx += count

    np.random.shuffle(base_an_indices)
    cl_indices = base_an_indices[:atom_counts['Cl']]
    delete_indices = base_an_indices[atom_counts['Cl']:]

    for i in cl_indices: atoms[i].symbol = 'Cl'
    del atoms[delete_indices]

    total_mass_g_mol = sum([atom_counts[el] * atomic_masses[atomic_numbers[el]] for el in elements])
    volume_cm3 = (total_mass_g_mol / 6.022e23) / args.density 
    liquid_box_length = (volume_cm3 * 1e24) ** (1/3)
    atoms.set_cell([liquid_box_length, liquid_box_length, liquid_box_length], scale_atoms=True)

    atoms.calc = calc

    # =========================================================
    # 2. OPTIMIZATION & MELT (THERMAL SEED ACTIVATED)
    # =========================================================
    # Switch to the unique array seed for the MD velocities
    np.random.seed(RANDOM_SEED)
    rng = np.random.RandomState(RANDOM_SEED)

    print("\n--- PHASE 0: GEOMETRY OPTIMIZATION ---", flush=True)
    atoms.rattle(stdev=0.1, rng=rng)
    opt = FIRE(atoms) # Removed the maxstep restriction
    opt.run(fmax=1.0, steps=1000)

    # =========================================================
    # DYNAMIC MELT PROTOCOL (Li & Zn SAFETY)
    # =========================================================
    has_lithium = 'Li' in elements
    has_zinc = 'Zn' in elements
    
    # 1. Mass Scaling for Melt (Prevents thrashing for Li)
    if has_lithium:
        print("Lithium detected: Temporarily scaling Li mass to Na mass for stability...", flush=True)
        masses = atoms.get_masses()
        for i, atom in enumerate(atoms):
            if atom.symbol == 'Li':
                masses[i] = 22.990 
        atoms.set_masses(masses)
    
    MELT_TEMP = 2500
    MELT_TIMESTEP = 0.5 if has_lithium else 1.0
    MELT_STEPS = int(10000 / MELT_TIMESTEP)

    print(f"\n--- PHASE 1: {MELT_TEMP}K MELT (Langevin NVT) ---", flush=True)
    MaxwellBoltzmannDistribution(atoms, temperature_K=MELT_TEMP, rng=rng)
    Stationary(atoms) # ADD THIS LINE
    dyn_melt = Langevin(atoms, timestep=MELT_TIMESTEP * units.fs, temperature_K=MELT_TEMP, friction=0.01)
    dyn_melt.run(MELT_STEPS)

    # 3. CRITICAL: Restore True Mass for Production Dynamics
    if has_lithium:
        print("Restoring true Lithium mass (6.94 amu) for valid dynamic calculation...", flush=True)
        true_masses = atoms.get_masses()
        for i, atom in enumerate(atoms):
            if atom.symbol == 'Li':
                true_masses[i] = 6.941
        atoms.set_masses(true_masses)

# =========================================================
    # 3. EQUILIBRATION & PRODUCTION (OPTIMIZED)
    # =========================================================
    print(f"\n--- PHASE 2: {TARGET_TEMP}K EQUILIBRATION (Bussi CSVR) ---", flush=True)
    MaxwellBoltzmannDistribution(atoms, temperature_K=TARGET_TEMP, rng=rng)
    dyn_equil = Bussi(atoms, timestep=1.0 * units.fs, temperature_K=TARGET_TEMP, taut=25.0 * units.fs)
    dyn_equil.run(20000) # 20 ps

    # --- NEW: NVE BURN-IN (NO RECORDING) ---
    print(f"\n--- PHASE 3a: {TARGET_TEMP}K NVE BURN-IN (80 ps) ---", flush=True)
    dyn_nve_burn = VelocityVerlet(atoms, timestep=1.0 * units.fs)
    dyn_nve_burn.run(80000) # 80 ps of silent equilibration

    # --- NEW: NVE PRODUCTION (RECORDING) ---
    print(f"\n--- PHASE 3b: {TARGET_TEMP}K NVE PRODUCTION (70 ps) ---", flush=True)
    dyn_nve_prod = VelocityVerlet(atoms, timestep=1.0 * units.fs)

    eV_to_J = 1.602176634e-19
    A_to_m = 1e-10
    amu_to_kg = 1.66053906660e-27
    ASE_velocity_to_ms = np.sqrt(eV_to_J / amu_to_kg)
    ASE_force_to_N = eV_to_J / A_to_m

    masses_kg = atoms.get_masses() * amu_to_kg
    V_m3 = atoms.get_volume() * (A_to_m**3)
    rho_kg_m3 = np.sum(masses_kg) / V_m3

    Lx_m, Ly_m, Lz_m = atoms.cell.cellpar()[:3] * A_to_m
    kx, ky, kz = 2*np.pi/Lx_m, 2*np.pi/Ly_m, 2*np.pi/Lz_m

    stresses_Pa, J_vals, Jdot_vals, T_vals = [], [], [], []

    def record_dynamics():
        vel_ms = atoms.get_velocities() * ASE_velocity_to_ms
        pos_m = atoms.get_positions() * A_to_m
        forces_N = atoms.get_forces() * ASE_force_to_N
        
        virial_stress_Pa = atoms.get_stress() * (eV_to_J / A_to_m**3)
        kin_xx_Pa = -np.sum(masses_kg * vel_ms[:, 0]**2) / V_m3
        kin_yy_Pa = -np.sum(masses_kg * vel_ms[:, 1]**2) / V_m3
        kin_zz_Pa = -np.sum(masses_kg * vel_ms[:, 2]**2) / V_m3
        
        stresses_Pa.append([virial_stress_Pa[0] + kin_xx_Pa, 
                            virial_stress_Pa[1] + kin_yy_Pa, 
                            virial_stress_Pa[2] + kin_zz_Pa])
        
        px = np.exp(-1j * kx * pos_m[:, 0])
        py = np.exp(-1j * ky * pos_m[:, 1])
        pz = np.exp(-1j * kz * pos_m[:, 2])
        
        Jx = np.sum(masses_kg * vel_ms[:, 0] * px)
        Jy = np.sum(masses_kg * vel_ms[:, 1] * py)
        Jz = np.sum(masses_kg * vel_ms[:, 2] * pz)
        
        Jdotx = np.sum((forces_N[:, 0] - 1j * kx * masses_kg * vel_ms[:, 0]**2) * px)
        Jdoty = np.sum((forces_N[:, 1] - 1j * ky * masses_kg * vel_ms[:, 1]**2) * py)
        Jdotz = np.sum((forces_N[:, 2] - 1j * kz * masses_kg * vel_ms[:, 2]**2) * pz)
        
        J_vals.append([np.abs(Jx)**2, np.abs(Jy)**2, np.abs(Jz)**2])
        Jdot_vals.append([np.abs(Jdotx)**2, np.abs(Jdoty)**2, np.abs(Jdotz)**2])
        T_vals.append(atoms.get_temperature())

    dyn_nve_prod.attach(record_dynamics, interval=10)
    dyn_nve_prod.run(70000) # 70 ps of pure, usable data collection

    # =========================================================
    # 4. CALCULATION
    # =========================================================
    print("\n--- PHASE 4: SPEED OF SOUND CALCULATION ---", flush=True)

    # No more slicing needed! All data is post-equilibration.
    converged_T_vals = T_vals
    converged_stresses = np.array(stresses_Pa)
    converged_J = np.array(J_vals)
    converged_Jdot = np.array(Jdot_vals)

    T_avg = np.mean(converged_T_vals)
    var_stress_avg = np.mean([np.var(converged_stresses[:, 0]), 
                              np.var(converged_stresses[:, 1]), 
                              np.var(converged_stresses[:, 2])])

    cinf2_x = (1 / kx**2) * (np.mean(converged_Jdot[:, 0]) / np.mean(converged_J[:, 0]))
    cinf2_y = (1 / ky**2) * (np.mean(converged_Jdot[:, 1]) / np.mean(converged_J[:, 1]))
    cinf2_z = (1 / kz**2) * (np.mean(converged_Jdot[:, 2]) / np.mean(converged_J[:, 2]))
    cinf2_avg = np.mean([cinf2_x, cinf2_y, cinf2_z])

    c_inf = np.sqrt(cinf2_avg)
    kB = 1.380649e-23
    fluct_term = (V_m3 / (rho_kg_m3 * kB * T_avg)) * var_stress_avg
    c_s2 = cinf2_avg - fluct_term
    c_s = np.sqrt(c_s2) if c_s2 > 0 else float('nan')

    print(f"Adiabatic Speed of Sound (c_s): {c_s:.2f} m/s", flush=True)

    output_filename = f"Vs_{args.comp}_seed_{RANDOM_SEED}_{int(args.temp)}K.txt"
    with open(output_filename, "w") as f:
        f.write(str(c_s))
    print(f"Result saved to {output_filename}", flush=True)

if __name__ == "__main__":
    main()