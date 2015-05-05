__author__ = 'Dennis'

import easl.utils
from agent import Agent


class Data(object):
    def __init__(self):
        """

        Attributes
        ----------
        entries : list
            list of dictionaries of variable name/value pairs
        """
        self.entries = []

    def add_entry(self, vals):
        self.entries.append(vals)

    def calculate_joint(self, names):
        """
        Calculates the joint probability distribution from data for the given
        variables.

        Parameters
        ----------
        names : [string]
            names of the variables to calculate the distribution for

        Returns
        -------
        Distribution
            the joint probability table
        """
        freq = easl.utils.Table(names)

        for entry in self.entries:
            freq.inc_value(entry)

        n = len(self.entries)
        freq.do_operation(lambda x: x / n)

        return easl.utils.Distribution(names, freq)


class CausalReasoningAgent(Agent):
    """
    Uses Causal Bayes Nets based learning.

    Needs
     - conversion of observations to Variables
     - actions as interventions

    Notes
    -----
    Based on work by Gopnik [1]_ and dissertation [2]_.

    Probability:
    http://www.saedsayad.com/naive_bayesian.htm

    References
    ----------
    .. [1] "Thing by Gopnik," Gopnik et al.
    .. [2] Dissertation
    """
    def __init__(self):
        super(CausalReasoningAgent, self).__init__()

        self.data = Data()

        self.actions = []
        self.observations = []

    def init_internal(self, actions):
        self.actions = actions

    def sense(self, observation):
        # Simply store the information to use later.
        self.observations.append(observation)

    def act(self):
        # TODO: Implement.
        # Convert observations into an entry in the Database.
        self.__store_observations()

        # Get the causal network for the observations.
        # TODO: How to get the variables?
        net = self.__learn_causality(variables)
        # Find the action that would create the optimal reward.
        # TODO: Where is the reward?
        # For now:
        #   Calculate the probability of the reward happening for all actions.
        #   Take the action with maximum reward.
        return []

    def __store_observations(self):
        """
        Takes the observations in this time step and stores them in the database.
        """
        self.data.add_entry(dict(self.observations))
        self.observations = []

    def __learn_causality(self, variables):
        """
        Constraint-based approach to learning the network.

        Parameters
        ----------
        variables : list
            network node names
        data : list of list
            contains data on variable instances used to check for independence
            a table of entries of lists of variable/value pairs
        """
        # 1. Form the complete undirected graph on all variables
        #
        # - form complete (undirected) graph of variables
        #  + node/edge representation
        #  + add node
        #  + add edge between nodes
        c = easl.utils.Graph()
        c.make_complete(variables)

        sepset = []

        # 2. Test each pair of variables for independence.
        #    Eliminate the edges between any pair of variables found to be
        #    independent.
        #
        #    P(A) * P(B) = P(A & B)
        #    P(B|A) = P(B)
        #    P(A|B) = P(A)
        #
        # - test two variables on independence given data
        # - eliminate edge between nodes
        # - calculate probability P(X) from data
        # - calculate probability P(X|Y) from data

        # Check independence by checking if P(A|B) = P(A)
        for i_a in range(len(variables)):
            a = variables[i_a]
            for b in variables[i_a+1:]:
                # Calculate P(A)
                p_a = self.data.calculate_joint([a])

                # Calculate P(B)
                p_b = self.data.calculate_joint([b])

                # Calculate P(A & B)
                p_ab = self.data.calculate_joint([a, b])

                # Check for independence by checking P(A & B) = P(A) * P(B)
                if CausalReasoningAgent.check_independence(p_a, p_b, p_ab):
                    c.del_edge(a, b)

        # 3. For each pair U, V of variables connected by an edge,
        #    and for each T connected to one or both U, V, test whether
        #    U _|_ V | T
        #    If an independence is found, remove the edge between U and V.
        #
        #    P(A,B|C) = P(A|C) * P(B|C)
        #    P(A,B,C)/P(C) = P(A,C)/P(C) * P(B,C)/P(C)
        #
        # - test three variables on conditional independence
        # - find all nodes connected to one node
        # Get all pairs of nodes connected by an edge
        for (u, v) in c.get_pairs():
            # Get all nodes connected to one of either nodes
            ts = set(c.get_connected(u) + c.get_connected(v))

            found = False

            for t in ts:
                # Test conditional independence
                # Calculate P(T), P(U,T), P(V,T) and P(U,V,T)
                p_t = self.data.calculate_joint([t])
                p_ut = self.data.calculate_joint([u, t])
                p_vt = self.data.calculate_joint([v, t])
                p_uvt = self.data.calculate_joint([u, v, t])

                if CausalReasoningAgent.check_independence_conditional([u, v, t],
                                                                               p_uvt, p_ut, p_vt, p_t):
                    found = True
                    continue

            if found:
                c.del_edge(u, v)
                sepset.append((u, v))
                sepset.append((v, u))
                continue

        # 4. For each pair U, V connected by an edge and each pair of T, S of
        #    variables, each of which is connected by an edge to either U or V,
        #    test the hypothesis that U _|_ V | {T, S}.
        #    If an independence is found, remove the edge between U, V.
        #
        #    P(A,B|C,D) = P(A|C,D) * P(B|C,D)
        #    P(A,B,C,D)/P(C,D) = P(A,C,D)/P(C,D) * P(B,C,D)/P(C,D)
        #
        # - test conditional independence on set of variables
        for (u, v) in c.get_pairs():
            ts = c.get_connected(u) + c.get_connected(v)

            found = False
            for (t, s) in [(t, s) for t in ts for s in ts if t != s]:
                p_uvst = self.data.calculate_joint([u, v, s, t])
                p_ust = self.data.calculate_joint([u, s, t])
                p_vst = self.data.calculate_joint([v, s, t])
                p_st = self.data.calculate_joint([s, t])

                if CausalReasoningAgent.check_independence_conditional([u, v, s, t],
                                                                               p_uvst, p_ust, p_vst, p_st):
                    found = True
                    continue

            if found:
                c.del_edge(u, v)
                sepset.append((u, v))
                sepset.append((v, u))
                continue

        # 5. For each triple of variables T, V, R such that T - V - R and
        #    there is no edge between T and R, orient as To -> V <- oR if
        #    and only if V was not conditioned on when removing the T - R
        #    edge.
        #
        #    The last part means to keep record of which edges were removed
        #    and to check against those.
        #
        #    According to Spirtes et al. this means leaving the original
        #    mark on the T and R nodes and putting arrow marks on the V
        #    end.
        #
        # - create marked edges (empty, o, >)
        # get triples T - V - R
        for (t, v, r) in c.get_triples():
            # if T - R not in sepset, orient edges
            if (t, r) not in sepset:
                c.orient(t, v, r)

        # 6. For each triple of variables T, V, R such that T has an edge
        #    with an arrowhead directed into V and V - R, and T has no edge
        #    connecting it to R, orient V - R as V -> R.
        for (t, v, r) in c.get_triples():
            c.orient_half(v, r)

        return c

    @staticmethod
    def check_independence(names, a, b, ab):
        """
        Checks the distributions according to P(A & B) = P(A) * P(B)

        Returns
        -------
        bool
            True if A and B pass the independence check, False otherwise
        """
        # Assume the distributions are correct
        # Get variables
        var_a, var_b = names
        v_a = a.get_variables()
        v_b = b.get_variables()

        for val_a in v_a[var_a]:
            for val_b in v_b[var_b]:
                # P(A & B) = P(A) * P(B)
                p_ab = ab.prob({var_a: val_a, var_b: val_b})
                p_a = a.prob({var_a: val_a})
                p_b = b.prob({var_b: val_b})

                # When the probabilities are not 'equal'
                if abs(p_ab - p_a * p_b) > 1e-6:
                    return False
        return True

    @staticmethod
    def check_independence_conditional(names, aby, ay, by, y):
        """
        Calculates the conditional probability.

        P(A,B|C) = P(A|C) * P(B|C)
        P(A,B,C)/P(C) = P(A,C)/P(C) * P(B,C)/P(C)

        Generalized:
        P(A,B|Y) = P(A|Y) * P(B|Y)
        P(A,B,Y) / P(Y) = P(A,Y) / P(Y) * P(B,Y) / P(Y)
        """
        v_aby = aby.get_variables()
        var_a = names[0]
        var_b = names[1]
        vars_y = names[2:]

        s_aby = {}
        s_ay = {}
        s_by = {}
        s_y = {}
        for val_a in v_aby[var_a]:
            s_aby[var_a] = val_a
            s_ay[var_a] = val_a
            for val_b in v_aby[var_b]:
                s_aby[var_b] = val_b
                s_by[var_b] = val_b
                for var_x in vars_y:
                    for val_x in vars_y[var_x]:
                        s_aby[var_x] = val_x
                        s_ay[var_x] = val_x
                        s_by[var_x] = val_x
                        s_y[var_x] = val_x

                        # P(A,B,C)/P(C) = P(A,C)/P(C) * P(B,C)/P(C)
                        p_aby = aby.prob(s_aby)
                        p_ay = ay.prob(s_ay)
                        p_by = by.prob(s_by)
                        p_y = y.prob(s_y)

                    # When the probabilities are not 'equal'
                    if abs(p_aby / p_y - (p_ay / p_y) * (p_by / p_y)) > 1e-6:
                        return False
        return True
