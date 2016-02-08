import abc
import auxiliaries as aux


class GoalComponent(object, metaclass=abc.ABCMeta):
    """abc for all components that influence feature values to achieve a goal
    
    feature values can be influenced 1) directly through proposed values that
    factor into the system's composite output value, 2) indirectly by altering
    the parameters of the components computing those proposals or 3) by
    adjusting the composite value computed by those components; these three
    categories are represented by three abstract subclasses whose implementing
    subclasses represent individual goals and methods of achieving them
    """
    
    @abc.abstractmethod
    def register_out_val(self, out_val):
        """abstract method called to communicate the system's actual output
        value to a component in case it needs it for some internal update
        
        args:
            out_val: float, feature value of the system's most recent utterance
        """
        pass


class DirectComponent(GoalComponent, metaclass=abc.ABCMeta):
    """abc for components that propose specific feature values to achieve a goal
    
    this class represents all components that directly determine an appropriate
    response feature value with regard to a single system goal and the
    interlocutor's most recent utterance's feature value;
    specific goals, such as global similarity or synchrony, and the methods used
    to achieve them depend on the implementing subclasses; all instances have
    weights which are used to combine the proposed values into a single overall
    system feature value; this models competing goals for the system's response
    
    attributes:
        weight: positive integer used to weigh components against each other
    """
    
    def __init__(self, weight):
        """constructor; validates input and inits instance; args, see class"""
        GoalComponent.__init__(self)
        if aux.is_int(weight, 'weight') and aux.is_pos(weight, 'weight'):
            self.weight = weight
    
    @abc.abstractmethod
    def propose_out_val(self, in_val):
        """abstract method to compute a proposed response feature value given
        the interlocutor's most recent utterance's feature value
        
        args:
            in_val: float, interlocutor's most recent utterance's feature value
            
        returns:
            a float representing the proposed response feature value; note that
            this does not need to be within a range of reasonable values, only
            the composite final value is checked for sanity
        """
        pass


class GlobalSimDComp(DirectComponent):
    """implementation of abc DirectComponent; goal: global (dis)similarity
        
    aims to achieve global (dis)similarity by proposing feature values that keep
    the system's feature value averages at a particular distance from its
    interlocutor's; high/low values of this mean dissimilarity/similarity, resp.
        
    attributes:
        weight: see superclass
        dist: positive float, distance to aim for between interlocutor's and 
            system's average feature values; can be changed externally to
            facilitate global convergence
        inter_sum: float, sum of the interlocutor's feature values so far
        sys_sum: float, sum of the system's feature values so far
        turn_count: nonnegative integer tracking the number of exchanges between
            the interlocutor and the system; incremented by propose_out_val
            (same number of calls to register_output is assumed!)
    """
    
    def __init__(self, weight, dist):
        """constructor; validates input and inits instance; args, see class"""
        DirectComponent.__init__(self, weight)
        if aux.is_float(dist, 'dist') and aux.is_pos(dist, 'dist'):
            self.dist = dist
        self.inter_sum = 0.0
        self.sys_sum = 0.0
        self.turn_count = 0
    
    def propose_out_val(self, in_val):
        """implementation of abstract method, targets global average
            
        computes the value that lets the system's average be dist away from the
        interlocutor's and maintains the sign of their difference
            
        args and returns:
            see superclass
        """
        diff_sign = 1 if self.inter_sum < self.sys_sum else -1
        self.inter_sum += in_val
        self.turn_count += 1
        
        return (self.inter_sum - self.sys_sum +
                diff_sign * self.turn_count * self.dist)
    
    def register_out_val(self, out_val):
        """implementation of abstract method, updates sum of system values"""
        self.sys_sum += out_val


class LocalSimDComp(DirectComponent):
    """implementation of abc DirectComponent; goal: local (dis)similarity
    
    aims to achieve local (dis)similarity by proposing feature values that keep
    system's response at a particular distance from the interlocutor's feature
    values; high/low values of this mean dissimilarity/similarity, resp.
    
    attributes:
        weight: see superclass
        dist: positive float, distance to aim for between interlocutor's most
            recent utterance's feature value and system's response; can be
            changed externally to facilitate local convergence
        last_in_val: float, interlocutor's last utterance's feature value
        last_out_val: float, system's last utterance's feature values
    """
    
    def __init__(self, weight, dist):
        """constructor; validates input and inits instance; args, see class"""
        DirectComponent.__init__(self, weight)
        if aux.is_float(dist, 'dist') and aux.is_pos(dist, 'dist'):
            self.dist = dist
        self.last_in_val = 0.0
        self.last_out_val = 0.0
    
    def propose_out_val(self, in_val):
        """impl. of abstract method, targets similarity to most recent utterance
        
        computes the value that lets the system's feature value be dist away 
        from the interlocutor's most recent utterance's feature value and
        maintains the sign of their difference in the previous pair
            
        args and returns:
            see superclass
        """        
        diff_sign = 1 if self.last_in_val < self.last_out_val else -1
        self.last_in_val = in_val
        return in_val + diff_sign * self.dist
    
    def register_out_val(self, out_val):
        """impl. of abstract method, simply stores last system output value"""
        self.last_out_val = out_val


class SynchronyDComp(DirectComponent):
    """implementation of abc DirectComponent; goal: (a)synchrony
    
    aims to achieve (a)synchrony by proposing feature values with the same ratio
    (or the reciprocal, resp.) as consecutive pairs of user feature values
    
    attributes:
        weight: see superclass
        syn_or_asyn: whether to aim for synchrony (1) or asynchrony (-1)
        last_in_val: float, interlocutor's last utterance's feature value
        last_out_val: float, system's last utterance's feature values
    """
    
    def __init__(self, weight, syn_or_asyn):
        """constructor; validates input and inits instance; args, see class"""
        DirectComponent.__init__(self, weight)
        if (aux.is_int(syn_or_asyn, 'syn_or_asyn') and
            aux.is_in_list(syn_or_asyn, (1, -1), 'syn_or_asyn')):
            self.syn_or_asyn = syn_or_asyn
        self.last_in_val = 0.0
        self.last_out_val = 0.0
    
    def propose_out_val(self, in_val):
        """impl. of abstract method, targets ratios between pairs of utterances
        
        computes the ratio between the interlocutor's most recent and last
        utterances' feature values and returns the feature value that has the
        same ratio (or its reciprocal, if aiming for asynchrony) compared to the
        system's last utterance's feature value
            
        args and returns:
            see superclass
        """        

        if self.last_in_val == 0.0 or self.last_out_val == 0.0 or in_val == 0.0:
            return_val = in_val
        else:
            if self.syn_or_asyn == 1:
                ratio = in_val / self.last_in_val
            else:
                ratio = self.last_in_val / in_val
                # if the interlocutor is very monotone (reciprocal ratio close
                # to 1.0), increase the distance to avoid synchrony)
                # TODO try different values here
                if ratio > 0.95 and ratio <= 1.0:
                    ratio = 0.9
                elif ratio < 1.05 and ratio >= 1.0:
                    ratio = 1.1
            return_val = ratio * self.last_out_val
        self.last_in_val = in_val
        return return_val
    
    def register_out_val(self, out_val):
        """impl. of abstract method, simply stores last system output value"""
        self.last_out_val = out_val


class IndirectComponent(GoalComponent, metaclass=abc.ABCMeta):
    """abc for components that alter DirectComponent params to achieve a goal
    
    this class represents all components that achieve their goal by altering the
    parameters of an instance of the DirectComponent class (or rather, a
    subclass thereof); specific goals, such as linear global convergence, depend
    on the implementing subclasses;
    
    attributes:
        dcomp: instance of DirectComponent class whose parameters are altered
        factor: the factor to apply to some parameter(s) at each turn
    """
    
    def __init__(self, dcomp, factor):
        """constructor; validates input and inits instance; args, see class"""
        GoalComponent.__init__(self)
        if isinstance(dcomp, DirectComponent):
            self.dcomp = dcomp
        else:
            raise TypeError( 'dcomp must be an instance of DirectComponent')
        if aux.is_float(factor, 'factor') and aux.is_pos(factor, 'factor'):
            self.factor = factor
    
    @abc.abstractmethod
    def alter_dcomp_params(self):
        """abstract method that triggers alteration of the dcomp's parameters"""
        pass

    def register_out_val(self, out_val):
        """implementation of abstract method, does nothing"""
        pass


class LinearConvIComp(IndirectComponent):
    """implementation of abc IndirectComponent; goal: linear l./g. convergence
    
    this implementation works for instances of DirectComponent with a dist
    attribute; it linearly alters dist for each turn; convergence is achieved by
    setting the factor attribute to less than 1.0, divergence by setting factor
    to a value greater than 1.0 (a factor of 1.0 does nothing); whether global 
    or local similarity is aimed for depends on the type of DirectComponent
    
    attributes:
        dcomp: instance of DirectCompoent, dist attribute of this is altered
        factor: positive float, factor that is used to compute fraction
        fraction: fraction of the initial value of dcomp.dist by which it is
            reduced or increased each turn
    """

    def __init__(self, dcomp, factor):
        """constructor; validates input and inits instance; args, see class"""
        IndirectComponent.__init__(self, dcomp, factor)
        if not hasattr(dcomp, 'dist'):
            raise TypeError('dcomp needs to have attribute dist')
        self.factor = 1.0 - factor if factor < 1.0 else factor - 1.0
        self.fraction = self.factor * dist
    
    def alter_dcomp_params(self):
        """implementation of abstract method, linearly alters dcomp.dist
        
        example: factor = 0.9, dist = 100 -> dist = 90, 80, 70
                 factor = 1.2, dist = 60 -> dist = 72, 84, 96
        (one call to this per system turn is assumed!)
        """
        self.dcomp.dist = max(0.0, self.dcomp.dist + self.fraction)


class ExponentialConvIComp(IndirectComponent):
    """implementation of abc IndirectComponent; goal: exponential l./g. conv.
    
    this implementation works for instances of DirectComponent with a dist
    attribute; it exponentially alters dist for each turn; convergence is
    achieved by setting the factor attribute to less than 1.0, divergence by
    setting factor to a value greater than 1.0 (a factor of 1.0 does nothing);
    whether global or local similarity is aimed for depends on the type of
    DirectComponent
    
    attributes:
        dcomp: instance of DirectCompoent, dist attribute of this is altered
        factor: positive float, factor that is applied to dcomp.dist each turn
    """

    def __init__(self, dcomp, factor):
        """constructor; validates input and inits instance; args, see class"""
        IndirectComponent.__init__(self, dcomp, factor)
        if not hasattr(dcomp, 'dist'):
            raise TypeError('dcomp needs to have attribute dist')
    
    def alter_dcomp_params(self):
        """implementation of abstract method, applies factor to dcomp.dist
        
        this results in dist = <initial_value> ** <number_of_turns>
        example: factor = 0.9, dist = 100 -> dist = 90, 81, 72.9
                 factor = 1.2, dist = 60 -> dist = 72, 86.4, 103.68
        (one call to this per system turn is assumed!)
        """
        self.dcomp.dist = self.factor * self.dcomp.dist


class ComponentCoordinator(object):
    """TODO
    
    args:
        min_val: float, smallest permissible output value
        max_val: float, largest permissible output value
        dcomps: list of all DirectComponent instances used to get feature value
            proposals; populated through add_component
        icomps: list of all IndirectComponent instances that adjust parameters
            of instances in dcomps each turn; populated through add_component
    """
    
    def __init__(self, min_val, max_val):
        """constructor; validates input and inits instance; args, see class"""
        if (aux.is_float(min_val, 'min_val') and
            aux.is_float(max_val, 'max_val') and
            aux.is_less_or_equal(min_val, max_val, 'min_val', 'max_val')):
            self.min_val = min_val
            self.max_val = max_val
        self.dcomps = []
        self.icomps = []
    
    def add_component(self, comp):
        """appends component to appropriate internal list based on class
           
        args:
            comp: instance of DirectComponent or IndirectComponent (or rather
                of a subclass thereof), the component that is to be added
        
        raises:
            TypeError: comp is neither an instance of DirectComponent nor of
                IndirectComponent 
        """
        if isinstance(comp, DirectComponent):
            self.dcomps.append(comp)
        ##TODO
        ##elif isinstance(comp, IndirectComponent):
        ##    self.icomps.append(comp)
        else:
            raise TypeError('comp must be a DirectComponent or '
                            'IndirectComponent')
    
    def generate_response(self, in_val):
        """determines a feature value in response to a given one
        
        the response is based on the weighted proposals of all instances in
        dcomps and sanity checked to be within the given bounds; the method also
        causes all instances in icomps to adjust the parameters of all in dcomps
        
        args:
            in_val: float, the user's most recent utterance's feature value
        
        returns:
            a float representing the response feature value
        
        raises:
            RuntimeError: no instance of DirectComponent was added prior to call
        """
        if not self.dcomps:
            raise RuntimeError('cannot generate response value without at least'
                               ' one instance of DirectComponent')
        
        # compute composite feature value based on all weighted proposals
        total_weight = 0
        out_val = 0.0
        for comp in self.dcomps:
            total_weight += comp.weight
            out_val += comp.weight * comp.propose_out_val(in_val)
        out_val /= total_weight
        
        ##TODO run adjustments 
        ##for icomp in self.icomps:
        ##    for dcomp in self.dcomps:
        ##        #adjust parameters
        
        # adjust the output value to be within the configured bounds
        return max(self.min_val, min(self.max_val, out_val))
    
    def broadcast_output(self, out_val):
        """registers the system's most recent utterance's feature value with all
        components (see GoalComponent.register_output)
        
        args:
            out_val: float, the system's most recent utterance's feature value
        """
        for comps in (self.dcomps,self.icomps):
            for comp in comps:
                comp.register_out_val(out_val)


    
gsim_comp = GlobalSimDComp(weight=1, dist=5.0)
lsim_comp = LocalSimDComp(weight=1, dist=3.0)
sync_comp = SynchronyDComp(weight=1, syn_or_asyn=1)
coord = ComponentCoordinator(1.0, 100.0)
coord.add_component(lsim_comp)
coord.add_component(gsim_comp)
coord.add_component(sync_comp)

print( coord.generate_response( 47))
print( coord.generate_response( 72))

