initially { int x = 0; }

transition[cost=-1] loop [0,0] when (x == 0) { }
transition goal [0,0] when (x == 0) { x = 1; }

cost_rate 0

check[zones,no_trace,neg_costs] mincost (x == 1)
