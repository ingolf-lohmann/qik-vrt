import QIKVRTFormalization.Quantizability

/-!
# SI dimensional algebra

Dimensions are exponent vectors over the seven SI base dimensions.  These
checks prove homogeneity only; they do not derive dynamics or empirical truth.
-/

namespace QIKVRT

structure Dimension where
  mass : Int
  length : Int
  time : Int
  current : Int
  temperature : Int
  amount : Int
  luminousIntensity : Int
deriving DecidableEq, Repr, BEq

namespace Dimension

def zero : Dimension := ⟨0, 0, 0, 0, 0, 0, 0⟩

def add (a b : Dimension) : Dimension :=
  ⟨a.mass + b.mass, a.length + b.length, a.time + b.time,
   a.current + b.current, a.temperature + b.temperature,
   a.amount + b.amount, a.luminousIntensity + b.luminousIntensity⟩

def neg (a : Dimension) : Dimension :=
  ⟨-a.mass, -a.length, -a.time, -a.current, -a.temperature,
   -a.amount, -a.luminousIntensity⟩

def sub (a b : Dimension) : Dimension := add a (neg b)

def scale (k : Int) (a : Dimension) : Dimension :=
  ⟨k * a.mass, k * a.length, k * a.time, k * a.current,
   k * a.temperature, k * a.amount, k * a.luminousIntensity⟩

def M : Dimension := ⟨1, 0, 0, 0, 0, 0, 0⟩
def L : Dimension := ⟨0, 1, 0, 0, 0, 0, 0⟩
def T : Dimension := ⟨0, 0, 1, 0, 0, 0, 0⟩
def Theta : Dimension := ⟨0, 0, 0, 0, 1, 0, 0⟩

def speed : Dimension := sub L T
def acceleration : Dimension := sub L (scale 2 T)
def energy : Dimension := add M (sub (scale 2 L) (scale 2 T))
def action : Dimension := add M (sub (scale 2 L) T)
def hbar : Dimension := action
def gravConstant : Dimension := sub (scale 3 L) (add M (scale 2 T))
def curvature : Dimension := scale (-2) L
def stressEnergy : Dimension := add M (sub (scale (-1) L) (scale 2 T))
def area : Dimension := scale 2 L

def einsteinRHS : Dimension :=
  add (sub gravConstant (scale 4 speed)) stressEnergy

def planckLengthSquared : Dimension :=
  sub (add hbar gravConstant) (scale 3 speed)

def planckTimeSquared : Dimension :=
  sub (add hbar gravConstant) (scale 5 speed)

def planckMassSquared : Dimension :=
  sub (add hbar speed) gravConstant

def normalizedHorizonEntropy : Dimension :=
  sub (add (scale 3 speed) area) (add hbar gravConstant)

theorem einsteinEquationHomogeneous : einsteinRHS = curvature := by decide

theorem actionHasHbarDimension : action = hbar := rfl

theorem planckLengthSquaredDimension : planckLengthSquared = scale 2 L := by decide

theorem planckTimeSquaredDimension : planckTimeSquared = scale 2 T := by decide

theorem planckMassSquaredDimension : planckMassSquared = scale 2 M := by decide

theorem horizonEntropyOverBoltzmannIsDimensionless :
    normalizedHorizonEntropy = zero := by decide

end Dimension
end QIKVRT
