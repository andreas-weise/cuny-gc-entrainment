class Entrainer(object):
    """    note: currently assumes user goes first and values are means

    attributes:
        default_val: default output value without any entrainment
        glo_weight: global entrainment weight
        loc_weight: local entrainment weight
        glo_conv: global convergence summand (added to glo_weight each turn)
        loc_conv: local convergence summand (added to loc_weight each turn)
        first_k: number of user turns k to use for average calculation
    """

    def __init__(self, def_val, init_glo_weight, init_loc_weight,
                 glo_conv, loc_conv, first_k):
        """constructor; initializes instance; args, see class

        applies some basic sanity checks to the input
        """
        self.def_val = def_val
        self.glo_weight = max(init_glo_weight, 0)
        self.loc_weight = max(init_loc_weight, 0)
        self.glo_weight_tmp = self.glo_weight
        self.loc_weight_tmp = self.loc_weight
        if self.glo_weight + self.loc_weight > 1:
            self.glo_weight = (self.glo_weight /
                               (self.glo_weight + self.loc_weight))
            self.loc_weight = (self.loc_weight /
                               (self.glo_weight + self.loc_weight))
        self.glo_conv = glo_conv
        self.loc_conv = loc_conv
        self.first_k = max(first_k, 1)
        self.def_weight = 1 - self.glo_weight - self.loc_weight
        # track the values of user and system turns
        self.user_turns = []
        self.system_turns = []

    def __str__(self):
        """returns string representation of the current configuration"""
        return (str(self.def_val) + ' ' + str(self.glo_weight) + ' ' +
                str(self.loc_weight) + ' ' + str(self.glo_conv) + ' ' +
                str(self.loc_conv) + ' ' + str(self.first_k))

    def register_input(self, val, len_s):
        """stores latest user input value

        if called mulitple times in a row without call to register_output in
        between, last user turn value will be updated as mean of these calls
        (supports multiple utterances within the same turn)

        args:
            val: input value
            len_s: length of the input in seconds
        """
        if len(self.user_turns) == len(self.system_turns):
            self.user_turns.append([val, len_s])
        else:
            last = self.user_turns.pop()
            average_val = (last[0] * last[1] + val * len_s) / (last[1] + len_s)
            self.user_turns.append([average_val, last[1] + len_s])

    def register_output(self, val, len_s):
        """analogous to register_input, with input/output reversed

        tracks actual output value (proposed value might not have been realized)
        """
        if len(self.system_turns) < len(self.user_turns):
            self.system_turns.append([val, len_s])
        else:
            last = self.system_turns.pop()
            average_val = (last[0] * last[1] + val * len_s) / (last[1] + len_s)
            self.system_turns.append([average_val, last[1] + len_s])

    def propose_output(self):

        if len(self.system_turns) < len(self.user_turns):
            # global component
            # 1) average of up to first_k user turns
            k = min(len(self.user_turns), self.first_k)
            k_average = sum(val[0] for val in self.user_turns[0:k]) / k
            # 2) sum of outputs so far
            out_sum = sum(val[0] for val in self.system_turns)
            # 3) necessary value to match average
            glo = len(self.user_turns) * k_average - out_sum
            # 4) weighted by global entrainment weight
            glo *= self.glo_weight

            # local component
            loc = self.loc_weight * self.user_turns[-1][0]

            proposed_val = self.def_weight * self.def_val + glo + loc

            # update weights with convergence summands
            self.glo_weight_tmp = max(self.glo_weight_tmp + self.glo_conv, 0)
            self.loc_weight_tmp = max(self.loc_weight_tmp + self.loc_conv, 0)
            if self.glo_weight_tmp + self.loc_weight_tmp > 1:
                self.glo_weight = (self.glo_weight_tmp /
                                   (self.glo_weight_tmp + self.loc_weight_tmp))
                self.loc_weight = (self.loc_weight_tmp /
                                   (self.glo_weight_tmp + self.loc_weight_tmp))
            else:
                self.glo_weight = self.glo_weight_tmp
                self.loc_weight = self.loc_weight_tmp
            self.def_weight = 1 - self.glo_weight - self.loc_weight
        else:
            proposed_val = self.system_turns[-1][0]
        return proposed_val

if __name__ == "__main__":
    pitches = [164, 127, 133, 125, 117, 139, 107, 99, 108, 110]
    entrainer = Entrainer(94, 0.3, 0.2, 0.1, 0.3, 12)
    for pitch in pitches:
        entrainer.register_input(pitch, 1)
        tmp = entrainer.propose_output()
        print(tmp)
        entrainer.register_output(tmp, 1)
