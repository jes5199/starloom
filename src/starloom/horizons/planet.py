"""Planet enum re-exported from starloom.planet for backward compatibility."""

import warnings
from ..planet import Planet

# Issue a DeprecationWarning
warnings.warn(
    "Importing Planet from starloom.horizons.planet is deprecated. "
    "Import from starloom.planet instead.",
    DeprecationWarning,
    stacklevel=2
)

from enum import Enum


class Planet(Enum):
    # Lights
    SUN = "10"
    MOON = "301"

    # Planets
    MERCURY = "199"
    VENUS = "299"
    EARTH = "399"
    MARS = "499"
    JUPITER = "599"
    SATURN = "699"
    URANUS = "799"
    NEPTUNE = "899"

    # Dwarf planets
    PLUTO = "999"  # aka "134340;"
    ERIS = "136199;"
    HAUMEA = "136108;"
    MAKEMAKE = "136472;"
    ORCUS = "90482;"
    QUAOAR = "50000;"
    SEDNA = "90377;"
    GONGGONG = "225088;"
    VARUNA = "20000;"
    IXION = "28978;"

    # Asteroids
    CERES = "1;"
    PALLAS = "2;"
    JUNO = "3;"
    VESTA = "4;"
    ASTRAEA = "5;"
    HEBE = "6;"
    IRIS = "7;"
    FLORA = "8;"
    METIS = "9;"
    HYGIEA = "10;"
    PARTHENOPE = "11;"
    VICTORIA = "12;"
    EGERIA = "13;"
    IRENE = "14;"
    EUNOMIA = "15;"
    PSYCHE = "16;"
    THETIS = "17;"
    MELOPOME = "18;"
    FORTUNA = "19;"
    MASSALIA = "20;"
    PROSERPINA = "26;"
    KALLIOPE = "22;"
    THEMIS = "24;"
    CIRCE = "34;"
    DAPHNE = "41;"
    ISIS = "42;"
    KLYTIA = "73;"
    FREIA = "76;"
    FRIGGA = "77;"
    DIANA = "78;"
    SAPPHO = "80;"
    LYSITHEA = "94;"
    HEKATE = "100;"
    MIRIAM = "102;"
    HERA = "103;"
    ALKESTE = "124;"
    PHAEDRA = "174;"
    PENELOPE = "201;"
    CLEOPATRA = "216;"
    ANNA = "265;"
    EMMA = "283;"
    EROS = "433;"
    VALENTINE = "447;"
    ASTARTE = "672;"
    CUPIDO = "763;"
    LILITH = "1181;"
    AMOR = "1221;"
    APHRODITE = "1388;"
    BODA = "1487;"
    UNION = "1585;"
    ICARUS = "1566;"
    ANTEROS = "1943;"
    APOLLO = "1862;"
    LANCELOT = "2041;"
    ADONIS = "2101;"
    ASMODEUS = "2174;"
    TOLKIEN = "2675;"
    VISHNU = "4034;"
    MILES = "4119;"
    CHILD = "4580;"
    GROOM = "5129;"
    HERACLES = "5143;"
    CASANOVA = "7328;"
    ISAAC_NEWTON = "8000;"
    DAVID_BOWIE = "342843;"

    # Centaurs
    CHIRON = "2060;"
    PHOLUS = "5145;"
    NESSUS = "7066;"
    CHARIKLO = "10199;"
    ASBOLUS = "8405;"
    OKYRHOE = "52872;"
    HYLONOME = "10370;"
    BIENOR = "54598;"
    ECHECLUS = "60558;"
