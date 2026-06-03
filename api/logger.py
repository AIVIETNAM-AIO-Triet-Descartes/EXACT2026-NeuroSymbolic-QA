[
    {
        "id": "formula_001",
        "topic": "ohms_law",
        "domain": "circuits",
        "formula_natural": "Ohm's law relating voltage, current, and resistance",
        "formula_sympy": "V = I * R",
        "formula_latex": "V = IR",
        "variables": {
            "V": {
                "description": "Voltage or potential difference",
                "unit": "V"
            },
            "I": {
                "description": "Electric current",
                "unit": "A"
            },
            "R": {
                "description": "Electrical resistance",
                "unit": "ohm"
            }
        },
        "unit_conversions": [
            "mA → 1e-3 A",
            "A → 1 A",
            "kohm → 1e3 ohm",
            "Mohm → 1e6 ohm",
            "mV → 1e-3 V",
            "kV → 1e3 V"
        ],
        "example_question": "A resistor of 5 kohm has a current of 2 mA flowing through it. Calculate the voltage across the resistor.",
        "example_cot": "Step 1: Identify R = 5 kohm = 5000 ohm, I = 2 mA = 0.002 A.\nStep 2: Apply V = I * R.\nStep 3: V = 0.002 * 5000 = 10 V.",
        "example_answer": "10",
        "example_unit": "V",
        "keywords": [
            "Ohm's law",
            "Ohm",
            "ohm",
            "resistance",
            "voltage",
            "current",
            "resistor",
            "potential difference",
            "V=IR",
            "V = IR",
            "calculate voltage",
            "find current",
            "determine resistance",
            "R",
            "I",
            "V"
        ]
    },
    {
        "id": "formula_002",
        "topic": "series_resistance",
        "domain": "circuits",
        "formula_natural": "Total resistance of resistors connected in series",
        "formula_sympy": "R_total = R1 + R2 + R3",
        "formula_latex": "R_{total} = R_1 + R_2 + R_3",
        "variables": {
            "R_total": {
                "description": "Equivalent total resistance",
                "unit": "ohm"
            },
            "R1": {
                "description": "Resistance of first resistor",
                "unit": "ohm"
            },
            "R2": {
                "description": "Resistance of second resistor",
                "unit": "ohm"
            },
            "R3": {
                "description": "Resistance of third resistor",
                "unit": "ohm"
            }
        },
        "unit_conversions": [
            "kohm → 1e3 ohm",
            "Mohm → 1e6 ohm"
        ],
        "example_question": "Three resistors with values 100 ohm, 200 ohm, and 300 ohm are connected in series. Find the total resistance.",
        "example_cot": "Step 1: Identify R1 = 100 ohm, R2 = 200 ohm, R3 = 300 ohm.\nStep 2: Apply R_total = R1 + R2 + R3.\nStep 3: R_total = 100 + 200 + 300 = 600 ohm.",
        "example_answer": "600",
        "example_unit": "ohm",
        "keywords": [
            "series resistance",
            "resistors in series",
            "equivalent resistance",
            "total resistance",
            "series circuit",
            "calculate total resistance",
            "find equivalent resistance",
            "R1",
            "R2",
            "R3",
            "R_total"
        ]
    },
    {
        "id": "formula_003",
        "topic": "parallel_resistance",
        "domain": "circuits",
        "formula_natural": "Equivalent resistance of two resistors connected in parallel",
        "formula_sympy": "R_total = (R1 * R2) / (R1 + R2)",
        "formula_latex": "R_{total} = \\frac{R_1 R_2}{R_1 + R_2}",
        "variables": {
            "R_total": {
                "description": "Equivalent total parallel resistance",
                "unit": "ohm"
            },
            "R1": {
                "description": "Resistance of first parallel resistor",
                "unit": "ohm"
            },
            "R2": {
                "description": "Resistance of second parallel resistor",
                "unit": "ohm"
            }
        },
        "unit_conversions": [
            "kohm → 1e3 ohm",
            "Mohm → 1e6 ohm"
        ],
        "example_question": "Two resistors of 20 ohm and 30 ohm are connected in parallel. Calculate their equivalent resistance.",
        "example_cot": "Step 1: Identify R1 = 20 ohm, R2 = 30 ohm.\nStep 2: Apply R_total = (R1 * R2) / (R1 + R2).\nStep 3: R_total = (20 * 30) / (20 + 30) = 600 / 50 = 12 ohm.",
        "example_answer": "12",
        "example_unit": "ohm",
        "keywords": [
            "parallel resistance",
            "resistors in parallel",
            "equivalent resistance",
            "parallel circuit",
            "total parallel resistance",
            "calculate parallel resistance",
            "find equivalent parallel",
            "R1",
            "R2",
            "R_total"
        ]
    },
    {
        "id": "formula_004",
        "topic": "power_vi",
        "domain": "circuits",
        "formula_natural": "Electric power using voltage and current",
        "formula_sympy": "P = V * I",
        "formula_latex": "P = VI",
        "variables": {
            "P": {
                "description": "Electric power consumed or generated",
                "unit": "W"
            },
            "V": {
                "description": "Voltage drop across the component",
                "unit": "V"
            },
            "I": {
                "description": "Current flowing through the component",
                "unit": "A"
            }
        },
        "unit_conversions": [
            "mW → 1e-3 W",
            "kW → 1e3 W",
            "MW → 1e6 W",
            "mA → 1e-3 A",
            "kV → 1e3 V"
        ],
        "example_question": "A device operates at a voltage of 12 V and draws a current of 2 A. Determine the power consumption.",
        "example_cot": "Step 1: Identify V = 12 V, I = 2 A.\nStep 2: Apply P = V * I.\nStep 3: P = 12 * 2 = 24 W.",
        "example_answer": "24",
        "example_unit": "W",
        "keywords": [
            "electric power",
            "power consumption",
            "power dissipated",
            "voltage and current",
            "watt",
            "calculate power",
            "find power",
            "determine wattage",
            "P = VI",
            "P=VI",
            "P",
            "V",
            "I"
        ]
    },
    {
        "id": "formula_005",
        "topic": "power_i2r",
        "domain": "circuits",
        "formula_natural": "Electric power dissipated in a resistor using current and resistance",
        "formula_sympy": "P = I**2 * R",
        "formula_latex": "P = I^2 R",
        "variables": {
            "P": {
                "description": "Power dissipated as heat",
                "unit": "W"
            },
            "I": {
                "description": "Current through the resistor",
                "unit": "A"
            },
            "R": {
                "description": "Resistance value",
                "unit": "ohm"
            }
        },
        "unit_conversions": [
            "mW → 1e-3 W",
            "kW → 1e3 W",
            "mA → 1e-3 A",
            "kohm → 1e3 ohm"
        ],
        "example_question": "Calculate the power dissipated by a 10 ohm resistor when a current of 3 A flows through it.",
        "example_cot": "Step 1: Identify R = 10 ohm, I = 3 A.\nStep 2: Apply P = I**2 * R.\nStep 3: P = (3**2) * 10 = 9 * 10 = 90 W.",
        "example_answer": "90",
        "example_unit": "W",
        "keywords": [
            "power dissipation",
            "Joule heating",
            "resistor power",
            "current and resistance",
            "calculate power heat",
            "find heat dissipation",
            "I**2 * R",
            "P=I^2R",
            "P",
            "I",
            "R"
        ]
    },
    {
        "id": "formula_006",
        "topic": "power_v2r",
        "domain": "circuits",
        "formula_natural": "Electric power dissipated in a resistor using voltage and resistance",
        "formula_sympy": "P = V**2 / R",
        "formula_latex": "P = \\frac{V^2}{R}",
        "variables": {
            "P": {
                "description": "Power dissipated",
                "unit": "W"
            },
            "V": {
                "description": "Voltage across the resistor",
                "unit": "V"
            },
            "R": {
                "description": "Resistance value",
                "unit": "ohm"
            }
        },
        "unit_conversions": [
            "mW → 1e-3 W",
            "kW → 1e3 W",
            "kV → 1e3 V",
            "kohm → 1e3 ohm"
        ],
        "example_question": "A 50 ohm resistor is connected across a 10 V battery. Find the power consumption.",
        "example_cot": "Step 1: Identify R = 50 ohm, V = 10 V.\nStep 2: Apply P = V**2 / R.\nStep 3: P = (10**2) / 50 = 100 / 50 = 2 W.",
        "example_answer": "2",
        "example_unit": "W",
        "keywords": [
            "power using voltage",
            "resistor power draw",
            "voltage and resistance",
            "calculate power from voltage",
            "V**2 / R",
            "P=V^2/R",
            "P",
            "V",
            "R"
        ]
    },
    {
        "id": "formula_007",
        "topic": "kvl",
        "domain": "circuits",
        "formula_natural": "Kirchhoff's Voltage Law for a single loop",
        "formula_sympy": "V_source - V1 - V2 = 0",
        "formula_latex": "V_{source} - V_1 - V_2 = 0",
        "variables": {
            "V_source": {
                "description": "Source voltage or EMF",
                "unit": "V"
            },
            "V1": {
                "description": "Voltage drop across first component",
                "unit": "V"
            },
            "V2": {
                "description": "Voltage drop across second component",
                "unit": "V"
            }
        },
        "unit_conversions": [
            "mV → 1e-3 V",
            "kV → 1e3 V"
        ],
        "example_question": "In a single loop circuit, the source voltage is 12 V. If the voltage drop across the first resistor is 4 V, find the voltage drop across the second resistor.",
        "example_cot": "Step 1: Identify V_source = 12 V, V1 = 4 V.\nStep 2: Apply KVL: V_source - V1 - V2 = 0.\nStep 3: 12 - 4 - V2 = 0 => V2 = 8 V.",
        "example_answer": "8",
        "example_unit": "V",
        "keywords": [
            "Kirchhoff's Voltage Law",
            "KVL",
            "loop rule",
            "conservation of energy",
            "voltage sum",
            "loop equation",
            "calculate voltage drop",
            "find loop voltage",
            "V_source",
            "V1",
            "V2"
        ]
    },
    {
        "id": "formula_008",
        "topic": "kcl",
        "domain": "circuits",
        "formula_natural": "Kirchhoff's Current Law for a node",
        "formula_sympy": "I_in - I_out1 - I_out2 = 0",
        "formula_latex": "I_{in} = I_{out1} + I_{out2}",
        "variables": {
            "I_in": {
                "description": "Total current entering the node",
                "unit": "A"
            },
            "I_out1": {
                "description": "First current leaving the node",
                "unit": "A"
            },
            "I_out2": {
                "description": "Second current leaving the node",
                "unit": "A"
            }
        },
        "unit_conversions": [
            "mA → 1e-3 A",
            "uA → 1e-6 A"
        ],
        "example_question": "A total current of 5 A enters a node. If 2 A leaves through one branch, how much current leaves through the second branch?",
        "example_cot": "Step 1: Identify I_in = 5 A, I_out1 = 2 A.\nStep 2: Apply KCL: I_in - I_out1 - I_out2 = 0.\nStep 3: 5 - 2 - I_out2 = 0 => I_out2 = 3 A.",
        "example_answer": "3",
        "example_unit": "A",
        "keywords": [
            "Kirchhoff's Current Law",
            "KCL",
            "junction rule",
            "node rule",
            "conservation of charge",
            "current entering leaving",
            "calculate branch current",
            "find node current",
            "I_in",
            "I_out"
        ]
    },
    {
        "id": "formula_009",
        "topic": "voltage_divider",
        "domain": "circuits",
        "formula_natural": "Voltage divider rule for output voltage across the second resistor",
        "formula_sympy": "V_out = V_in * R2 / (R1 + R2)",
        "formula_latex": "V_{out} = V_{in} \\frac{R_2}{R_1 + R_2}",
        "variables": {
            "V_out": {
                "description": "Output voltage across R2",
                "unit": "V"
            },
            "V_in": {
                "description": "Input source voltage",
                "unit": "V"
            },
            "R1": {
                "description": "Resistance of first resistor",
                "unit": "ohm"
            },
            "R2": {
                "description": "Resistance of second resistor",
                "unit": "ohm"
            }
        },
        "unit_conversions": [
            "kV → 1e3 V",
            "mV → 1e-3 V",
            "kohm → 1e3 ohm"
        ],
        "example_question": "An input voltage of 10 V is applied to a series combination of R1 = 40 ohm and R2 = 60 ohm. Find the output voltage across R2.",
        "example_cot": "Step 1: Identify V_in = 10 V, R1 = 40 ohm, R2 = 60 ohm.\nStep 2: Apply V_out = V_in * R2 / (R1 + R2).\nStep 3: V_out = 10 * 60 / (40 + 60) = 600 / 100 = 6 V.",
        "example_answer": "6",
        "example_unit": "V",
        "keywords": [
            "voltage divider",
            "voltage splitting",
            "attenuator",
            "series voltage drop",
            "calculate output voltage",
            "find V_out",
            "voltage divider formula",
            "V_in",
            "V_out",
            "R1",
            "R2"
        ]
    },
    {
        "id": "formula_010",
        "topic": "current_divider",
        "domain": "circuits",
        "formula_natural": "Current divider rule for the first branch of two parallel resistors",
        "formula_sympy": "I1 = I_total * R2 / (R1 + R2)",
        "formula_latex": "I_1 = I_{total} \\frac{R_2}{R_1 + R_2}",
        "variables": {
            "I1": {
                "description": "Current through branch 1 with resistor R1",
                "unit": "A"
            },
            "I_total": {
                "description": "Total entering current",
                "unit": "A"
            },
            "R1": {
                "description": "Resistance of branch 1",
                "unit": "ohm"
            },
            "R2": {
                "description": "Resistance of branch 2",
                "unit": "ohm"
            }
        },
        "unit_conversions": [
            "mA → 1e-3 A",
            "kohm → 1e3 ohm"
        ],
        "example_question": "A total current of 6 A enters a parallel combination of R1 = 10 ohm and R2 = 20 ohm. Calculate the current through the 10 ohm resistor.",
        "example_cot": "Step 1: Identify I_total = 6 A, R1 = 10 ohm, R2 = 20 ohm.\nStep 2: Apply I1 = I_total * R2 / (R1 + R2).\nStep 3: I1 = 6 * 20 / (10 + 20) = 120 / 30 = 4 A.",
        "example_answer": "4",
        "example_unit": "A",
        "keywords": [
            "current divider",
            "current splitting",
            "parallel current branch",
            "calculate branch current",
            "find branch current",
            "current divider formula",
            "I_total",
            "I1",
            "R1",
            "R2"
        ]
    },
    {
        "id": "formula_011",
        "topic": "capacitor_charge",
        "domain": "electrostatics",
        "formula_natural": "Electric charge stored in a capacitor",
        "formula_sympy": "Q = C * V",
        "formula_latex": "Q = CV",
        "variables": {
            "Q": {
                "description": "Stored electrical charge",
                "unit": "C"
            },
            "C": {
                "description": "Capacitance",
                "unit": "F"
            },
            "V": {
                "description": "Voltage across the capacitor",
                "unit": "V"
            }
        },
        "unit_conversions": [
            "uF → 1e-6 F",
            "nF → 1e-9 F",
            "pF → 1e-12 F",
            "uC → 1e-6 C",
            "mC → 1e-3 C",
            "mV → 1e-3 V"
        ],
        "example_question": "A 50 uF capacitor is connected to a 12 V source. Calculate the accumulated charge on the capacitor.",
        "example_cot": "Step 1: Identify C = 50 uF = 5e-5 F, V = 12 V.\nStep 2: Apply Q = C * V.\nStep 3: Q = 5e-5 * 12 = 6e-4 C = 0.0006 C.",
        "example_answer": "0.0006",
        "example_unit": "C",
        "keywords": [
            "capacitor charge",
            "charge stored",
            "capacitance and voltage",
            "Coulomb",
            "find charge",
            "calculate electric charge",
            "Q=CV",
            "Q = CV",
            "Q",
            "C",
            "V"
        ]
    },
    {
        "id": "formula_012",
        "topic": "capacitor_energy",
        "domain": "electrostatics",
        "formula_natural": "Energy stored in a capacitor",
        "formula_sympy": "E = 0.5 * C * V**2",
        "formula_latex": "E = \\frac{1}{2}CV^2",
        "variables": {
            "E": {
                "description": "Stored electrostatic energy",
                "unit": "J"
            },
            "C": {
                "description": "Capacitance",
                "unit": "F"
            },
            "V": {
                "description": "Voltage across the capacitor",
                "unit": "V"
            }
        },
        "unit_conversions": [
            "uF → 1e-6 F",
            "nF → 1e-9 F",
            "mF → 1e-3 F",
            "mJ → 1e-3 J",
            "uJ → 1e-6 J"
        ],
        "example_question": "Calculate the energy stored in capacitor C when C = 100 μF and V = 30 V.",
        "example_cot": "Step 1: Identify C = 100 μF = 1e-4 F, V = 30 V.\nStep 2: Apply E = 0.5 * C * V**2.\nStep 3: E = 0.5 * 1e-4 * 30**2 = 0.5 * 1e-4 * 900 = 0.045 J.",
        "example_answer": "0.045",
        "example_unit": "J",
        "keywords": [
            "capacitor energy",
            "energy stored",
            "capacitance",
            "voltage",
            "stored energy",
            "electrostatic energy",
            "calculate stored energy",
            "find capacitor energy",
            "0.5 * C * V**2",
            "E",
            "C",
            "V"
        ]
    },
    {
        "id": "formula_013",
        "topic": "series_capacitance",
        "domain": "electrostatics",
        "formula_natural": "Equivalent capacitance of two capacitors connected in series",
        "formula_sympy": "C_total = (C1 * C2) / (C1 + C2)",
        "formula_latex": "C_{total} = \\frac{C_1 C_2}{C_1 + C_2}",
        "variables": {
            "C_total": {
                "description": "Equivalent series capacitance",
                "unit": "F"
            },
            "C1": {
                "description": "Capacitance of first capacitor",
                "unit": "F"
            },
            "C2": {
                "description": "Capacitance of second capacitor",
                "unit": "F"
            }
        },
        "unit_conversions": [
            "uF → 1e-6 F",
            "nF → 1e-9 F",
            "pF → 1e-12 F"
        ],
        "example_question": "Two capacitors of 3 uF and 6 uF are connected in series. What is their total equivalent capacitance?",
        "example_cot": "Step 1: Identify C1 = 3 uF, C2 = 6 uF.\nStep 2: Apply C_total = (C1 * C2) / (C1 + C2).\nStep 3: C_total = (3 * 6) / (3 + 6) = 18 / 9 = 2 uF.",
        "example_answer": "2",
        "example_unit": "uF",
        "keywords": [
            "series capacitance",
            "capacitors in series",
            "equivalent capacitance series",
            "calculate series capacitance",
            "find total capacitance series",
            "C1",
            "C2",
            "C_total"
        ]
    },
    {
        "id": "formula_014",
        "topic": "parallel_capacitance",
        "domain": "electrostatics",
        "formula_natural": "Equivalent capacitance of capacitors connected in parallel",
        "formula_sympy": "C_total = C1 + C2",
        "formula_latex": "C_{total} = C_1 + C_2",
        "variables": {
            "C_total": {
                "description": "Equivalent total parallel capacitance",
                "unit": "F"
            },
            "C1": {
                "description": "Capacitance of first capacitor",
                "unit": "F"
            },
            "C2": {
                "description": "Capacitance of second capacitor",
                "unit": "F"
            }
        },
        "unit_conversions": [
            "uF → 1e-6 F",
            "nF → 1e-9 F",
            "pF → 1e-12 F"
        ],
        "example_question": "A 4 uF capacitor and a 6 uF capacitor are wired in parallel. Determine the total capacitance.",
        "example_cot": "Step 1: Identify C1 = 4 uF, C2 = 6 uF.\nStep 2: Apply C_total = C1 + C2.\nStep 3: C_total = 4 + 6 = 10 uF.",
        "example_answer": "10",
        "example_unit": "uF",
        "keywords": [
            "parallel capacitance",
            "capacitors in parallel",
            "total capacitance parallel",
            "calculate parallel capacitance",
            "find total capacitance parallel",
            "C1",
            "C2",
            "C_total"
        ]
    },
    {
        "id": "formula_015",
        "topic": "electric_field_uniform",
        "domain": "electrostatics",
        "formula_natural": "Uniform electric field between parallel plates",
        "formula_sympy": "E = V / d",
        "formula_latex": "E = \\frac{V}{d}",
        "variables": {
            "E": {
                "description": "Electric field strength",
                "unit": "V/m"
            },
            "V": {
                "description": "Potential difference between plates",
                "unit": "V"
            },
            "d": {
                "description": "Distance separating the plates",
                "unit": "m"
            }
        },
        "unit_conversions": [
            "cm → 1e-2 m",
            "mm → 1e-3 m",
            "kV → 1e3 V"
        ],
        "example_question": "Two parallel plates are separated by a distance of 2 cm and have a potential difference of 100 V. Find the electric field strength.",
        "example_cot": "Step 1: Identify V = 100 V, d = 2 cm = 0.02 m.\nStep 2: Apply E = V / d.\nStep 3: E = 100 / 0.02 = 5000 V/m.",
        "example_answer": "5000",
        "example_unit": "V/m",
        "keywords": [
            "electric field",
            "uniform electric field",
            "voltage and distance",
            "parallel plates field",
            "calculate electric field",
            "find field strength",
            "E = V/d",
            "E",
            "V",
            "d"
        ]
    },
    {
        "id": "formula_016",
        "topic": "coulombs_law",
        "domain": "electrostatics",
        "formula_natural": "Coulomb's law for electrostatic force between two point charges",
        "formula_sympy": "F = k * q1 * q2 / r**2",
        "formula_latex": "F = k \\frac{q_1 q_2}{r^2}",
        "variables": {
            "F": {
                "description": "Electrostatic force of attraction or repulsion",
                "unit": "N"
            },
            "k": {
                "description": "Coulomb constant (8.99e9)",
                "unit": "N*m**2/C**2"
            },
            "q1": {
                "description": "Magnitude of first point charge",
                "unit": "C"
            },
            "q2": {
                "description": "Magnitude of second point charge",
                "unit": "C"
            },
            "r": {
                "description": "Separation distance between charges",
                "unit": "m"
            }
        },
        "unit_conversions": [
            "uC → 1e-6 C",
            "nC → 1e-9 C",
            "cm → 1e-2 m",
            "mm → 1e-3 m"
        ],
        "example_question": "Two charges of 2 uC and 3 uC are separated by 0.3 meters in a vacuum. Calculate the electrostatic force between them using k = 9e9.",
        "example_cot": "Step 1: Identify q1 = 2e-6 C, q2 = 3e-6 C, r = 0.3 m, k = 9e9.\nStep 2: Apply F = k * q1 * q2 / r**2.\nStep 3: F = 9e9 * 2e-6 * 3e-6 / (0.3**2) = 0.054 / 0.09 = 0.6 N.",
        "example_answer": "0.6",
        "example_unit": "N",
        "keywords": [
            "Coulomb's law",
            "electrostatic force",
            "point charges",
            "electric force",
            "attraction force",
            "repulsion force",
            "calculate electrostatic force",
            "find electric force",
            "F",
            "k",
            "q1",
            "q2",
            "r"
        ]
    },
    {
        "id": "formula_017",
        "topic": "electric_potential_energy",
        "domain": "electrostatics",
        "formula_natural": "Electric potential energy of a two point charge system",
        "formula_sympy": "U = k * q1 * q2 / r",
        "formula_latex": "U = k \\frac{q_1 q_2}{r}",
        "variables": {
            "U": {
                "description": "Electric potential energy",
                "unit": "J"
            },
            "k": {
                "description": "Coulomb constant (8.99e9)",
                "unit": "N*m**2/C**2"
            },
            "q1": {
                "description": "Charge of particle 1",
                "unit": "C"
            },
            "q2": {
                "description": "Charge of particle 2",
                "unit": "C"
            },
            "r": {
                "description": "Distance between charges",
                "unit": "m"
            }
        },
        "unit_conversions": [
            "uC → 1e-6 C",
            "nC → 1e-9 C",
            "cm → 1e-2 m",
            "mJ → 1e-3 J"
        ],
        "example_question": "Find the electric potential energy of two point charges of 1 uC and 4 uC separated by a distance of 2 meters with k = 9e9.",
        "example_cot": "Step 1: Identify q1 = 1e-6 C, q2 = 4e-6 C, r = 2 m, k = 9e9.\nStep 2: Apply U = k * q1 * q2 / r.\nStep 3: U = 9e9 * 1e-6 * 4e-6 / 2 = 0.036 / 2 = 0.018 J.",
        "example_answer": "0.018",
        "example_unit": "J",
        "keywords": [
            "electric potential energy",
            "electrostatic potential energy",
            "energy of charges",
            "calculate potential energy",
            "find charge energy",
            "U",
            "k",
            "q1",
            "q2",
            "r"
        ]
    },
    {
        "id": "formula_018",
        "topic": "capacitor_dielectric",
        "domain": "electrostatics",
        "formula_natural": "Capacitance of a parallel plate capacitor with a dielectric material",
        "formula_sympy": "C = epsilon * A / d",
        "formula_latex": "C = \\frac{\\epsilon A}{d}",
        "variables": {
            "C": {
                "description": "Capacitance of the parallel plate capacitor",
                "unit": "F"
            },
            "epsilon": {
                "description": "Permittivity of the dielectric material",
                "unit": "F/m"
            },
            "A": {
                "description": "Overlap area of the plates",
                "unit": "m**2"
            },
            "d": {
                "description": "Distance between plates",
                "unit": "m"
            }
        },
        "unit_conversions": [
            "cm2 → 1e-4 m2",
            "mm → 1e-3 m",
            "pF → 1e-12 F",
            "uF → 1e-6 F"
        ],
        "example_question": "A capacitor has plate area of 0.02 m2 and plate separation of 0.001 m. If the permittivity epsilon is 4e-11 F/m, calculate the capacitance.",
        "example_cot": "Step 1: Identify A = 0.02 m2, d = 0.001 m, epsilon = 4e-11 F/m.\nStep 2: Apply C = epsilon * A / d.\nStep 3: C = 4e-11 * 0.02 / 0.001 = 8e-13 / 0.001 = 8e-10 F.",
        "example_answer": "8e-10",
        "example_unit": "F",
        "keywords": [
            "dielectric capacitor",
            "parallel plate capacitance",
            "permittivity",
            "plate area",
            "plate separation",
            "calculate capacitance plates",
            "find capacitance area",
            "C",
            "epsilon",
            "A",
            "d"
        ]
    },
    {
        "id": "formula_019",
        "topic": "electric_potential_point",
        "domain": "electrostatics",
        "formula_natural": "Electric potential due to a single point charge",
        "formula_sympy": "V = k * q / r",
        "formula_latex": "V = k \\frac{q}{r}",
        "variables": {
            "V": {
                "description": "Electric potential",
                "unit": "V"
            },
            "k": {
                "description": "Coulomb constant (8.99e9)",
                "unit": "N*m**2/C**2"
            },
            "q": {
                "description": "Source point charge value",
                "unit": "C"
            },
            "r": {
                "description": "Distance from the point charge",
                "unit": "m"
            }
        },
        "unit_conversions": [
            "uC → 1e-6 C",
            "nC → 1e-9 C",
            "cm → 1e-2 m",
            "kV → 1e3 V"
        ],
        "example_question": "Calculate the electric potential at a distance of 0.5 meters from a point charge of 5 uC using k = 9e9.",
        "example_cot": "Step 1: Identify q = 5e-6 C, r = 0.5 m, k = 9e9.\nStep 2: Apply V = k * q / r.\nStep 3: V = 9e9 * 5e-6 / 0.5 = 45000 / 0.5 = 90000 V.",
        "example_answer": "90000",
        "example_unit": "V",
        "keywords": [
            "electric potential",
            "potential from point charge",
            "voltage from charge",
            "calculate electric potential",
            "find point potential",
            "V = kq/r",
            "V",
            "k",
            "q",
            "r"
        ]
    },
    {
        "id": "formula_020",
        "topic": "electric_field_point",
        "domain": "electrostatics",
        "formula_natural": "Electric field intensity due to a single point charge",
        "formula_sympy": "E = k * q / r**2",
        "formula_latex": "E = k \\frac{q}{r^2}",
        "variables": {
            "E": {
                "description": "Electric field strength",
                "unit": "N/C"
            },
            "k": {
                "description": "Coulomb constant (8.99e9)",
                "unit": "N*m**2/C**2"
            },
            "q": {
                "description": "Source point charge value",
                "unit": "C"
            },
            "r": {
                "description": "Distance from point charge",
                "unit": "m"
            }
        },
        "unit_conversions": [
            "uC → 1e-6 C",
            "nC → 1e-9 C",
            "cm → 1e-2 m"
        ],
        "example_question": "Find the electric field strength at a point 3 meters away from a 2e-5 C point charge with k = 9e9.",
        "example_cot": "Step 1: Identify q = 2e-5 C, r = 3 m, k = 9e9.\nStep 2: Apply E = k * q / r**2.\nStep 3: E = 9e9 * 2e-5 / (3**2) = 180000 / 9 = 20000 N/C.",
        "example_answer": "20000",
        "example_unit": "N/C",
        "keywords": [
            "electric field strength",
            "point charge field",
            "field intensity",
            "calculate field from charge",
            "find electric field intensity",
            "E = kq/r^2",
            "E",
            "k",
            "q",
            "r"
        ]
    }
]