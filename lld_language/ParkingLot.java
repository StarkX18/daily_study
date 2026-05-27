/*

Design a Parking Lot System.
Functional:

Multiple floors, slot sizes: SMALL, MEDIUM, LARGE
Vehicle types: BIKE, CAR, TRUCK — each fits certain slot sizes (bike fits any, car fits medium/large, truck only large)
Operations: park(vehicle) → issues a Ticket; exit(ticket) → returns the fee
Pricing varies by slot type + duration → must be swappable (different lots, different pricing models)

Non-functional:

Thread-safe by default. Two trucks pulling in simultaneously must not both get the last large slot.
Clean OOP. Idiomatic Java. Composition over inheritance where it fits.
No over-engineering — don't ship a 30-class enterprise monstrosity. Easy/Medium scope.

Expected deliverable (in order):

Class/interface skeleton — what are your types and how do they relate?
park() and exit() — the actual logic, including slot search
Where the locks live — and why there and not somewhere else
How PricingStrategy plugs in — show the interface and one concrete impl

What I'm specifically evaluating (so you optimize for this, not pretty code):

Slot-search strategy and its complexity
Concurrency: granularity of locking (lot-wide vs floor-wide vs per-slot — which and why)
Strategy pattern wiring — composition, not inheritance
Whether your design survives adding a new vehicle type without rewriting

*/

public enum SlotType {
    SMALL, MEDIUM, LARGE
}

public enum SlotStatus {
    EMPTY, FILLED
}


// --- compatibility matrix --- a new way to map vehicle types to slot types without changing existing code!!!!

public enum VehicleType {
    BIKE(EnumSet.of(SlotType.SMALL, SlotType.MEDIUM, SlotType.LARGE)),
    CAR(EnumSet.of(SlotType.MEDIUM, SlotType.LARGE)),
    TRUCK(EnumSet.of(SlotType.LARGE));

    private final Set<SlotType> compatibleSlots;
    
    VehicleType(Set<SlotType> c) {
        this.compatibleSlots = c;
    }

    public boolean fitsIn(SlotType s) {
        return compatibleSlots.contains(s);
    }
}

// --- domain ---
public class Vehicle {

    private final String licensePlate;
    private final VehicleType type;
    // ctor + getters
}

public class ParkingSlot {

    private final String slotId;
    private final SlotType type;
    private SlotStatus status = SlotStatus.EMPTY;
    private Vehicle occupant;          // null when empty
    private Instant occupiedSince;     // null when empty
    // synchronized methods OR rely on Floor-level lock — see below
}

public class Floor {

    private final int floorNumber;
    private final List<ParkingSlot> slots;
    private final Lock floorLock = new ReentrantLock();   // ← THE lock

    public Optional<ParkingSlot> tryAllocate(VehicleType vt) {
        floorLock.lock();
        try {
            for (ParkingSlot s : slots) {
                if (s.getStatus() == SlotStatus.EMPTY && vt.fitsIn(s.getType())) {
                    s.occupy(/* vehicle, now */);
                    return Optional.of(s);
                }
            }
            return Optional.empty();
        } finally {
            floorLock.unlock();
        }
    }

    public void release(ParkingSlot s) {
        floorLock.lock();
        try {
            s.vacate();
        } finally {
            floorLock.unlock();
        }
    }
}

// --- strategy ---
public interface PricingStrategy {
    BigDecimal computeFee(SlotType type, Duration parked);
}

public class FlatRatePricing implements PricingStrategy {
    /* ... */
}

public class TieredHourlyPricing implements PricingStrategy {
    /* ... */
}

// --- orchestrator ---
public class ParkingLot {

    private final List<Floor> floors;
    private final PricingStrategy pricing;       // composition
    private final Map<String, Ticket> activeTickets = new ConcurrentHashMap<>();

    public ParkingLot(List<Floor> floors, PricingStrategy pricing) {
        this.floors = floors;
        this.pricing = pricing;
    }

    public Ticket park(Vehicle v) {
        for (Floor f : floors) {
            Optional<ParkingSlot> slot = f.tryAllocate(v.getType());
            if (slot.isPresent()) {
                Ticket t = new Ticket(UUID.randomUUID().toString(),
                        v, slot.get(), f, Instant.now());
                activeTickets.put(t.getId(), t);
                return t;
            }
        }
        throw new LotFullException();
    }

    public BigDecimal exit(String ticketId) {
        Ticket t = activeTickets.remove(ticketId);
        if (t == null) {
            throw new InvalidTicketException();
        }
        BigDecimal fee = pricing.computeFee(
                t.getSlot().getType(),
                Duration.between(t.getEntryTime(), Instant.now())
        );
        t.getFloor().release(t.getSlot());
        return fee;
    }
}

// --- gates (pull-based, no observer for now) ---
public class EntryGate {

    private final ParkingLot lot;

    public Ticket admit(Vehicle v) {
        return lot.park(v);
    }
}

public class ExitGate {

    private final ParkingLot lot;
    private final PaymentProcessor payments;

    public void release(String ticketId) {
        BigDecimal fee = lot.exit(ticketId);
        payments.collect(fee);
    }
}
