from copy import deepcopy

i = 0
card_dim = [135,80,10]
dimensions = [0,0,0]

#Laid flat
for i in range(0,50):
    if i % 2 != 0:
        dimensions[0] += card_dim[0]
    else:
        dimensions[1] += card_dim[1]
dimensions[2] = card_dim[2]
flat = deepcopy(dimensions)

#Stacked
stacks = 2
dimensions[0] = card_dim[0] 
dimensions[1] = card_dim[1] * stacks
dimensions[2] = card_dim[2] * (50 / stacks)


print(f"Laid flat the cards are: {flat[0]}mm by {flat[1]}mm by {flat[2]}mm")
print(f"Stacked the cards are: {dimensions[0]}mm by {dimensions[1]}mm by {dimensions[2]}mm")

