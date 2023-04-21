import numpy as np
from fractions import Fraction
from collections import Counter
import sympy as sp
from biotuner.biotuner_utils import scale2frac, getPairs


def scale2euclid(scale, max_denom=10, mode="normal"):
    """
    Generate Euclidean rhythms based on a list of scale factors.

    Parameters
    ----------
    scale : List of float
        A list of positive floats representing the scale steps.
    max_denom : int, default=10
        An integer representing the maximum denominator allowed for the
        fractions generated by scale2frac().
    mode : str, default='normal'
        A string representing the mode of Euclidean rhythms to generate.
        Mode options:
            'normal' : generate rhythms with `num` steps distributed over `denom`
                       beats.
            'full' : generate rhythms with all possible combinations
                     of `num` and `denom` for a given `scale`.\

    Returns
    -------
    euclid_patterns : List of lists
        A list of lists containing the Euclidean rhythms generated
        by the function.

    Raises
    ------
    TypeError
        If `scale` is not a list of positive floats, or `max_denom` is not
        an integer.
    ValueError
        If `max_denom` is not a positive integer.

    Notes
    -----
    The `scale` parameter is first converted into fractions using the scale2frac()
    function. Euclidean rhythms are then generated based on the `num` and `denom`
    values of the fractions, using the bjorklund() function. If `mode` is set
    to "normal", the function generates one rhythm for each fraction where
    `denom` is less than or equal to `max_denom`. If `mode` is set to "full",
    the function generates all possible combinations of `num` and `denom` for
    each fraction where `denom` is less than or equal to `max_denom`.

    Examples
    --------
    >>> scale2euclid([1.33, 1.5, 1.75], max_denom=8, mode="normal")
    [[1, 1, 1, 0], [1, 1, 0], [1, 0, 1, 0, 1, 0, 1]]

    >>> scale2euclid([1.33, 1.5, 1.75], max_denom=8, mode="full")
    [[1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0],
    [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
    [1, 0, 1, 0, 1, 0], [1, 0, 0, 1, 0, 0],
    [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
    [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]]
     """
    euclid_patterns = []
    frac, num, denom = scale2frac(scale, maxdenom=max_denom)
    if mode == "normal":
        for n, d in zip(num, denom):
            if d <= max_denom:
                try:
                    euclid_patterns.append(bjorklund(n, d))
                except:
                    pass
    if mode == "full":
        for d, n in zip(num, denom):
            if d <= max_denom:
                steps = d * n
                try:
                    euclid_patterns.append(bjorklund(steps, d))
                    euclid_patterns.append(bjorklund(steps, n))
                except:
                    pass
    return euclid_patterns


def invert_ratio(ratio: float, n_steps_down: int, limit_denom: int = 64):
    """
    Inverts a given ratio by dividing 1 by it, then dividing the result by the ratio n_steps_down times.

    Parameters
    -----------
    ratio : float
        The ratio to be inverted.
    n_steps_down : int
        The number of times to divide the ratio.
    limit_denom : int, default=64
        The maximum denominator of the fraction returned.

    Returns
    --------
    Tuple [sp.Rational, float]
    
        - The resulting fraction after dividing 1 by the ratio and then dividing it n_steps_down times.
        - The resulting float after dividing 1 by the ratio and then dividing it n_steps_down times.
    """
    inverted_ratio = 1 / (ratio)
    i = 2
    if n_steps_down >= 1:
        while i <= n_steps_down:

            inverted_ratio = inverted_ratio / ratio
            i += 1

    frac = sp.Rational(inverted_ratio).limit_denominator(limit_denom)
    return frac, inverted_ratio


def binome2euclid(binome, n_steps_down=1, limit_denom=64):
    """
    Convert a binomial distribution of two ratios to Euclidean rhythms.

    Parameters
    ----------
    binome : list of two floats
        The two ratios to be converted.
    n_steps_down : int, default=1
        The number of times to apply the inversion operator.
    limit_denom : int, default=64
        The maximum denominator to be used when approximating fractions.

    Returns
    -------
    tuple
        - the generated Euclidean rhythms
        - the inverted ratios
        - the approximated fractions.

    Notes
    -----
    The Euclidean rhythms are generated using the bjorklund algorithm, as implemented in the bjorklund function. The
    input ratios are inverted according to the number of steps specified by the n_steps_down parameter. The resulting
    ratios are then used to generate a pair of approximated fractions, which are combined to produce the final
    Euclidean rhythms.
    """
    euclid_patterns = []
    new_binome = []
    new_frac1, b1 = invert_ratio(binome[0], n_steps_down, limit_denom=limit_denom)
    new_frac2, b2 = invert_ratio(binome[1], n_steps_down, limit_denom=limit_denom)
    new_binome.append(b1)
    new_binome.append(b2)
    frac, num, denom = scale2frac(new_binome, limit_denom)
    if denom[0] != denom[1]:
        new_denom = denom[0] * denom[1]
        try:
            euclid_patterns.append(bjorklund(new_denom, num[0] * denom[1]))
            euclid_patterns.append(bjorklund(new_denom, num[1] * denom[0]))
        except:
            pass

    else:
        new_denom = denom[0]

        try:
            euclid_patterns.append(bjorklund(new_denom, num[0]))
            euclid_patterns.append(bjorklund(new_denom, num[1]))
        except:
            pass

    return (
        euclid_patterns,
        [new_frac1, new_frac2],
        [[num[0] * denom[1], new_denom], [num[1] * denom[0], new_denom]],
    )


def consonant_euclid(scale, n_steps_down=2, limit_denom=64, limit_cons=0.1, limit_denom_final=16):
    """
    Computes Euclidean rhythms and consonant steps between them based on a given scale.

    Parameters
    ----------
    scale : list of floats
        Musical scale.
    n_steps_down : int, defaulty=2
        The number of steps the Euclidean rhythms is shifted down.
    limit_denom : int, default=64
        The upper bound of the denominator of the resulting fractions.
    limit_cons : float, default=0.1
        The lower bound of the consonance measure.
    limit_denom_final : int, default=16
        The upper bound of the denominator of the final consonant steps.

    Returns
    -------
    euclid_final, cons_step : (list[list], list[int])
        A tuple containing the following elements:
        - List of lists representing the Euclidean rhythms that satisfy the given consonance measure and denominator bounds.
        - List of integers representing the consonant steps between the Euclidean rhythms.

    """
    pairs = getPairs(scale)
    new_steps = []
    euclid_final = []
    for p in pairs:
        euclid, fracs, new_ratios = binome2euclid(p, n_steps_down, limit_denom)
        # print('new_ratios', new_ratios)
        new_steps.append(new_ratios[0][1])
    pairs_steps = getPairs(new_steps)
    cons_steps = []
    for steps in pairs_steps:
        # print(steps)
        try:
            steps1 = Fraction(steps[0] / steps[1]).limit_denominator(steps[1]).numerator
            steps2 = (
                Fraction(steps[0] / steps[1]).limit_denominator(steps[1]).denominator
            )
            # print(steps1, steps2)
            cons = (steps1 + steps2) / (steps1 * steps2)
            if (
                cons >= limit_cons
                and steps[0] <= limit_denom_final
                and steps[1] <= limit_denom_final
            ):
                cons_steps.append(steps[0])
                cons_steps.append(steps[1])
        except:
            continue
    for p in pairs:
        euclid, fracs, new_ratios = binome2euclid(p, n_steps_down, limit_denom)
        if new_ratios[0][1] in cons_steps:

            try:
                euclid_final.append(euclid[0])
                euclid_final.append(
                    euclid[1]
                )  # exception for when only one euclid has been computed (when limit_denom is very low, chances to have a division by zero)
            except:
                pass
    euclid_final = sorted(euclid_final)
    euclid_final = [
        euclid_final[i]
        for i in range(len(euclid_final))
        if i == 0 or euclid_final[i] != euclid_final[i - 1]
    ]
    euclid_final = [i for i in euclid_final if len(Counter(i).keys()) != 1]
    return euclid_final, cons_steps


def interval_vector(euclid):
    """
    Computes the interval vector for a given Euclidean rhythm.

    Parameters
    ----------
    euclid : array_like
        A binary array representing a Euclidean rhythm. Must have at least one pulse.

    Returns
    -------
    Interval_vector : numpy.ndarray
        An interval vector as a numpy array.

    Examples
    --------
    >>> euclid = [1, 1, 0, 1, 1, 0, 1]
    >>> interval_vector(euclid)
    array([1, 2, 1, 2, 1])

    >>> euclid = [1, 0, 0, 1, 0, 0, 1]
    >>> interval_vector(euclid)
    array([3, 3, 1])
    """
    indexes = [index + 1 for index, char in enumerate(euclid) if char == 1]
    length = len(euclid) + 1
    vector = [t - s for s, t in zip(indexes, indexes[1:])]
    vector = vector + [length - indexes[-1]]
    return vector


def bjorklund(steps, pulses):
    """
    Generate a Euclidean rhythm pattern using Bjorklund's algorithm.
    From https://github.com/brianhouse/bjorklund

    Parameters
    ----------
    steps : int
        The number of steps in the pattern.
    pulses : int
        The number of pulses in the pattern.

    Returns
    -------
    pattern : numpy.ndarray
        A binary Euclidean rhythm pattern with the specified number of steps and pulses.

    Raises
    ------
    ValueError
        If `pulses` is greater than `steps`.

    Examples
    --------
    Generate a Euclidean rhythm pattern with 16 steps and 5 pulses:

    >>> bjorklund(16, 5)
    array([1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0])

    """
 
    steps = int(steps)
    pulses = int(pulses)
    if pulses > steps:
        raise ValueError
    pattern = []
    counts = []
    remainders = []
    divisor = steps - pulses
    remainders.append(pulses)
    level = 0
    while True:
        counts.append(divisor // remainders[level])
        remainders.append(divisor % remainders[level])
        divisor = remainders[level]
        level = level + 1
        if remainders[level] <= 1:
            break
    counts.append(divisor)

    def build(level):
        if level == -1:
            pattern.append(0)
        elif level == -2:
            pattern.append(1)
        else:
            for i in range(0, counts[level]):
                build(level - 1)
            if remainders[level] != 0:
                build(level - 2)

    build(level)
    i = pattern.index(1)
    pattern = pattern[i:] + pattern[0:i]
    return pattern


def interval_vec_to_string(interval_vectors):
    """
    Convert a list of interval vectors to a list of string representations.
    
    Parameters
    ----------
    interval_vectors : list of array_like
        A list of interval vectors, where each interval vector is an array_like object representing
        the number of steps between each hit.
        
    Returns
    -------
    strings : list of str
        A list of string representations of the interval vectors, where each string is of the form
        'E(n,k)', where n is the number of hits and k is the number of steps.
    
    Examples
    --------
    >>> interval_vectors = [[2, 2, 2, 2, 1], [3, 3, 1]]
    >>> interval_vec_to_string(interval_vectors)
    ['E(5,9)', 'E(3,7)']
    """
    strings = []
    for i in interval_vectors:
        strings.append("E(" + str(len(i)) + "," + str(sum(i)) + ")")
    return strings


def euclid_string_to_referent(strings, dict_rhythms):
    """
    This function takes a list of strings of Euclidean rhythms represented in the E(n,k) format
    and returns a list of their referents in the given dictionary of rhythms.

    Parameters
    ----------
    strings : list of str
        A list of Euclidean rhythms represented as E(n,k) strings.
    dict_rhythms : dict
        A dictionary of rhythms where keys are the E(n,k) representation and values are the referents.

    Returns
    -------
    referent : list of str
        A list of the referents of the input rhythms. "None" is used for rhythms not found in the dictionary.

    Examples
    --------
    >>> from biotuner.dictionaries import dict_rhythms
    >>> strings = ["E(5,9)", "E(9,16)"]
    >>> euclid_string_to_referent(strings, dict_rhythms)
    ['It is a popular Arabic rhythm called Agsag-Samai. Started on the second onset,
    it is a drum pattern used by the Venda in South Africa, as well as a Rumanian folk-dance rhythm.
    It is also the rhythmic pattern of the Sigaktistos rhythm of Greece,
    and the Samai aktsak rhythm of Turkey. Started on the third onset,
    it is the rhythmic pattern of the Nawahiid rhythm of Turkey.',
    'It is a rhythm necklace used in the Central African Republic.
    When it is started on the second onset it is a bell pattern of
    the Luba people of Congo. When it is started on the fourth onset
    it is a rhythm played in West and Central Africa, as well as a cow-bell
    pattern in the Brazilian samba. When it is started on the penultimate onset
    it is the bell pattern of the Ngbaka-Maibo rhythms of the Central African Republic.']
    """
    referent = []
    for s in strings:
        if s in dict_rhythms.keys():
            referent.append(dict_rhythms[s])
        else:
            referent.append("None")
    return referent


def euclid_long_to_short(pattern):
    """Converts a long Euclidean rhythm pattern to a short representation.

    Parameters
    ----------
    pattern : list of int
        The long Euclidean rhythm pattern, represented as a list of integers 
        where 1 represents a hit and 0 represents a rest.

    Returns
    -------
    list of int
        A list with two integers representing the short representation of the 
        rhythm. The first integer represents the number of hits in the rhythm 
        and the second integer represents the total number of steps.

    Examples
    --------
    >>> euclid_long_to_short([1, 0, 1, 0, 1, 0, 1])
    [3, 7]
    """
    steps = len(pattern)
    hits = pattern.count(1)
    return [hits, steps]
