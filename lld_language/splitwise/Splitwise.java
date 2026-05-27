package splitwise;

import java.math.BigDecimal;
import java.time.Instant;

public class Group {
    Set<User> users;
    List<Transaction> transactions;
    Map<User, Map<User, BigDecimal>> runningBalances;

    public boolean settle(User A, User B) {
    }
    
    public boolean simplifyDebts(){

    }
}

public record User (
    UUID userId;
    String name;
){}

    public abstract class Transaction {
    public string id
    public string groupId
    Instant createdAt;
    Instant updatedAt;
    BigDecimal amount;
    User createdBy;

    public abstract boolean applyToBalanceGraph();
}

public class Expense extends Transaction {
    List<User> participants;
    Map<User, BigDecimal> shares;
    SplitStrategy splitStrategy;
    public boolean applyToBalanceGraph(){};
}

public class Settlement extends Transaction {
    User from;
    User to;
    public boolean applyToBalanceGraph();
}

public enum SplitStrategy {
    EQUAL {
        @Override
        public Map<User, BigDecimal> computeShares(
            BigDecimal total, List<User> participants, Object metadata) {
            // equal split logic
        }
    },
    EXACT {
        @Override public Map<User, BigDecimal> computeShares(BigDecimal total, List<User> participants, Object metadata) {...} 
    },
    PERCENTAGE  { 
        @Override public Map<User, BigDecimal> computeShares(BigDecimal total, List<User> participants, Object metadata) 
        {...} 
    };

    public abstract Map<User, BigDecimal> computeShares(BigDecimal total, List<User> participants, Object metadata);
}

public class Splitwise {
    Set<Group> groupList;

    public static void main(String[] args) {}
}
