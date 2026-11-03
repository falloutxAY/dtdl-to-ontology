"""Local v1 vocabulary facts from the DTDL quantitativeTypes specification.

Source: https://github.com/Azure/opendigitaltwins-dtdl/blob/master/DTDL/v3/
DTDL.quantitativeTypes.v1.md . No contexts are fetched during conversion.
"""

QUANTITATIVE = "dtmi:dtdl:extension:quantitativeTypes;1"
ANNOTATION = "dtmi:dtdl:extension:annotation;1"
ANNOTATION_V2 = "dtmi:dtdl:extension:annotation;2"
OVERRIDING = "dtmi:dtdl:extension:overriding;1"
OVERRIDING_V2 = "dtmi:dtdl:extension:overriding;2"
HISTORIZATION = "dtmi:dtdl:extension:historization;1"
HISTORIZATION_V2 = "dtmi:dtdl:extension:historization;2"
REQUIREMENT = "dtmi:dtdl:extension:requirement;1"
MQTT_V1 = "dtmi:dtdl:extension:mqtt;1"
MQTT_V2 = "dtmi:dtdl:extension:mqtt;2"
MQTT_V3 = "dtmi:dtdl:extension:mqtt;3"

EXTENSIONS = {
    QUANTITATIVE,
    ANNOTATION,
    ANNOTATION_V2,
    OVERRIDING,
    OVERRIDING_V2,
    HISTORIZATION,
    HISTORIZATION_V2,
    REQUIREMENT,
    MQTT_V1,
    MQTT_V2,
    MQTT_V3,
}

QUANTITY_UNITS = {
    name: unit
    for name, unit in (
        line.split()
        for line in """
Acceleration AccelerationUnit
Angle AngleUnit
AngularAcceleration AngularAccelerationUnit
AngularVelocity AngularVelocityUnit
ApparentEnergy ApparentEnergyUnit
ApparentPower ApparentPowerUnit
Area AreaUnit
Capacitance CapacitanceUnit
Concentration Unitless
Current CurrentUnit
DataRate DataRateUnit
DataSize DataSizeUnit
Density DensityUnit
Distance LengthUnit
ElectricCharge ChargeUnit
Energy EnergyUnit
EnergyRate PowerUnit
Force ForceUnit
Frequency FrequencyUnit
Humidity DensityUnit
Illuminance IlluminanceUnit
Inductance InductanceUnit
IonizingRadiationDose IonizingRadiationDoseUnit
Irradiance IrradianceUnit
Latitude AngleUnit
Length LengthUnit
Longitude AngleUnit
Luminance LuminanceUnit
Luminosity PowerUnit
LuminousFlux LuminousFluxUnit
LuminousIntensity LuminousIntensityUnit
MagneticFlux MagneticFluxUnit
MagneticInduction MagneticInductionUnit
Mass MassUnit
MassFlowRate MassFlowRateUnit
Power PowerUnit
Pressure PressureUnit
Radioactivity RadioactivityUnit
ReactiveEnergy ReactiveEnergyUnit
ReactivePower ReactivePowerUnit
RelativeDensity Unitless
RelativeHumidity Unitless
Resistance ResistanceUnit
SoundPressure SoundPressureUnit
Temperature TemperatureUnit
Thrust ForceUnit
TimeSpan TimeUnit
Torque TorqueUnit
Velocity VelocityUnit
Voltage VoltageUnit
Volume VolumeUnit
VolumeFlowRate VolumeFlowRateUnit
""".strip().splitlines()
    )
}

UNIT_VALUES = {
    name: tuple(values.split())
    for name, values in {
        "AccelerationUnit": "centimetrePerSecondSquared gForce metrePerSecondSquared",
        "AngleUnit": "degreeOfArc minuteOfArc radian secondOfArc turn",
        "AngularAccelerationUnit": "radianPerSecondSquared",
        "AngularVelocityUnit": (
            "degreePerSecond radianPerSecond revolutionPerMinute revolutionPerSecond"
        ),
        "ApparentEnergyUnit": (
            "gigavoltAmpereHour kilovoltAmpereHour megavoltAmpereHour voltAmpereHour"
        ),
        "ApparentPowerUnit": (
            "gigavoltAmpere kilovoltAmpere megavoltAmpere millivoltAmpere voltAmpere"
        ),
        "AreaUnit": (
            "acre hectare squareCentimetre squareFoot squareInch squareKilometre "
            "squareMetre squareMillimetre"
        ),
        "CapacitanceUnit": "farad microfarad millifarad nanofarad picofarad",
        "Unitless": (
            "partsPerBillion partsPerMillion partsPerQuadrillion partsPerTrillion percent unity"
        ),
        "CurrentUnit": "ampere kiloampere microampere milliampere",
        "DataRateUnit": (
            "bitPerSecond bytePerSecond exbibitPerSecond exbibytePerSecond gibibitPerSecond "
            "gibibytePerSecond kibibitPerSecond kibibytePerSecond mebibitPerSecond "
            "mebibytePerSecond tebibitPerSecond tebibytePerSecond yobibitPerSecond "
            "yobibytePerSecond zebibitPerSecond zebibytePerSecond"
        ),
        "DataSizeUnit": (
            "bit byte exbibit exbibyte gibibit gibibyte kibibit kibibyte mebibit mebibyte "
            "tebibit tebibyte yobibit yobibyte zebibit zebibyte"
        ),
        "DensityUnit": (
            "gramPerCubicMetre kilogramPerCubicMetre microgramPerCubicMetre milligramPerCubicMetre"
        ),
        "LengthUnit": (
            "astronomicalUnit centimetre foot inch kilometre metre micrometre "
            "mile millimetre nanometre nauticalMile"
        ),
        "ChargeUnit": "ampereHour coulomb milliampereHour",
        "EnergyUnit": (
            "britishThermalUnit electronvolt gigajoule gigawattHour joule kiloBritishThermalUnit "
            "kilojoule kilowattHour megaelectronvolt megajoule megawattHour milliwattHour "
            "terawattHour wattHour"
        ),
        "PowerUnit": (
            "britishThermalUnitPerHour gigajoulePerHour gigawatt horsepower joulePerHour "
            "joulePerSecond kiloBritishThermalUnitPerHour kilojoulePerHour kilojoulePerSecond "
            "kilowatt kilowattHourPerYear megajoulePerHour megawatt microwatt milliwatt "
            "tonOfRefrigeration watt"
        ),
        "ForceUnit": "newton ounce pound ton",
        "FrequencyUnit": "gigahertz hertz kilohertz megahertz millihertz",
        "IlluminanceUnit": "footcandle lux",
        "InductanceUnit": "henry microhenry millihenry",
        "IonizingRadiationDoseUnit": "gray microgray microsievert milligray millisievert sievert",
        "IrradianceUnit": "wattPerSquareMetre",
        "LuminanceUnit": "candelaPerSquareMetre",
        "LuminousFluxUnit": "lumen",
        "LuminousIntensityUnit": "candela",
        "MagneticFluxUnit": "maxwell weber",
        "MagneticInductionUnit": "gauss tesla",
        "MassUnit": "gram kilogram massPound microgram milligram slug tonne",
        "MassFlowRateUnit": (
            "gramPerHour gramPerSecond kilogramPerHour kilogramPerSecond massPoundPerHour"
        ),
        "PressureUnit": (
            "bar decapascal hectopascal inchesOfMercury inchesOfWater kilopascal "
            "millibar millimetresOfMercury pascal poundPerSquareInch"
        ),
        "RadioactivityUnit": "becquerel gigabecquerel kilobecquerel megabecquerel",
        "ReactiveEnergyUnit": (
            "gigavoltAmpereReactiveHour kilovoltAmpereReactiveHour "
            "megavoltAmpereReactiveHour voltAmpereReactiveHour"
        ),
        "ReactivePowerUnit": (
            "gigavoltAmpereReactive kilovoltAmpereReactive megavoltAmpereReactive "
            "millivoltAmpereReactive voltAmpereReactive"
        ),
        "ResistanceUnit": "kiloohm megaohm milliohm ohm",
        "SoundPressureUnit": "bel decibel",
        "TemperatureUnit": "degreeCelsius degreeFahrenheit kelvin",
        "TimeUnit": "day hour microsecond millisecond minute nanosecond second year",
        "TorqueUnit": "newtonMetre",
        "VelocityUnit": (
            "centimetrePerSecond kilometrePerHour kilometrePerSecond knot metrePerHour "
            "metrePerSecond milePerHour milePerSecond"
        ),
        "VoltageUnit": "kilovolt megavolt microvolt millivolt volt",
        "VolumeUnit": (
            "cubicCentimetre cubicFoot cubicInch cubicMetre fluidOunce gallon litre millilitre"
        ),
        "VolumeFlowRateUnit": (
            "cubicFootPerMinute cubicMetrePerHour cubicMetrePerMinute cubicMetrePerSecond "
            "gallonPerHour gallonPerMinute litrePerHour litrePerMinute litrePerSecond "
            "millilitrePerHour millilitrePerMinute millilitrePerSecond"
        ),
    }.items()
}
