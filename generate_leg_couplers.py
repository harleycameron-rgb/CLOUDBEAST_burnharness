from couplers._resolver import resolve_all_couplers


def generate_leg_couplers():
    return resolve_all_couplers()


if __name__ == "__main__":
    for c in generate_leg_couplers():
        print(c)
