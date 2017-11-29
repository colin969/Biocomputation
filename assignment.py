import random
from random import randint
import sys
import math
import re
import csv
import time

# VARIABLES #

P = 500 # Population Size
N = 10 # Number of Rules
N_min = 5 # Minimum number of Rules
G = 1000 # Number of Generations
m_chance = 0.01 # Decimal % chance of mutation
c_chance = 0.955 # Decimal % chance of crossover
roulette = False # Toggle Roulette Wheel selection instead of Tournament selection
save = True # Save best of a population before next population
file_name = "data1.txt" # File containing example data
gene_alphabet = ['#', 0, 1]

class Rule:
    def __init__(self, rule, out):
        self.rule = rule
        self.out = out

    def __str__(self):
        return "Rule {} - Output {}".format(self.rule, self.out)

class Individual:
    def __init__(self, rules=N, min_rules=N_min, create_genes=False, rule_length=0, output_length=0):
        # Creates initial N genes (random 0 or 1)
        if create_genes:
            genes = []
            for i in range(rules):
                # Output or Rule check
                for j in range(rule_length):
                    genes.append(random.choice(gene_alphabet))
                for j in range(output_length):
                    genes.append(random.choice([0,1]))
            self.genes = genes
        else:
            self.genes = []

        # Initial rule count to consider in fitness
        self.rule_num = randint(min_rules,rules)

        self.fitness = 0

    def __str__(self):
        return "Gene {} - Fitness {} - Rules {}".format(self.genes, self.fitness, self.rule_num)

class Population:
    def setup(self, size=P, rules=N, min_rules=N_min, mutate_chance=m_chance, print_info=True,
                crossover_chance=c_chance, roulette=roulette, save=save, dataset=file_name):
        self.roulette = roulette
        self.size = size
        self.rules = rules
        self.min_rules = min_rules
        self.mutate_chance = mutate_chance
        self.crossover_chance = crossover_chance
        self.save = save
        self.print_info = print_info

        # Start logging process
        self.start_csv()

        # Load data set for fitness function
        self.load_data(dataset=file_name)

        self.single_gene_length = self.rule_length + self.out_length
        self.gene_length = self.single_gene_length * rules

        # Generate initial population
        population = []
        for i in range(size):
            individual = Individual(create_genes=True, rule_length=self.rule_length, output_length=self.out_length)
            population.append(individual)
        self.population = population
        self.evaluate(self.population)
        # Start generation counter
        self.generation = 1
        self.write_current_generation()

    def start_csv(self):
        timestr = time.strftime("%Y%m%d-%H%M%S")
        headers = ["Generation", "Worst", "Best", "Best Rules", "Total", "Mean"]
        filestr = "{}_C{}_M{}_{}.csv".format(file_name.split(".")[0], str(self.crossover_chance * 100), str(self.mutate_chance * 100), timestr)
        self.open_file = open(filestr, "w", newline='')
        writer = csv.writer(self.open_file)
        writer.writerow(headers)
        self.writer = writer

    def end_csv(self):
        self.open_file.close()

    def write_current_generation(self):
        self.writer.writerow([self.generation, self.worst_fitness, self.best_fitness, self.best_rules, self.total_fitness, round(self.total_fitness / len(self.population), 2)])

    def load_data(self, dataset=file_name):
        dset = []
        with open(dataset) as f:
            content = f.readlines()

            # Pull rule and output length via split of first line
            self.rule_length = len(content[1].split(" ")[0])
            self.out_length = len(content[1].split(" ")[-1]) - 1
            if self.print_info:
                print("Rule Length of {} loaded from dataset".format(self.rule_length))
                print("Output Length of {} loaded from dataset".format(self.out_length))

            # Load in every rule
            for i in content[1:]:
                # E.G 01110 becomes [0,1,1,1,0]
                int_list = []
                # Read rule
                for j in i.split(" ")[0]:
                    int_list.append(int(j))
                rule = list(int_list)
                int_list = []

                # Read output, strip newline chars first
                for j in i.split(" ")[-1]:
                    str_list = list(j.rstrip())
                    for k in str_list:
                        int_list.append(int(k))
                output = list(int_list)

                output = list(int_list)
                int_list = []
                example = Rule(rule,output)
                dset.append(example)
        if self.print_info:
            print("Data Loaded - {} Examples".format(len(dset)))
        self.max_fitness = len(dset)
        self.dataset = dset

    def get_best(self, pop):
        best = pop[0]

        for i in pop:
            if i.fitness > best.fitness:
                best = i

        return best

    def next_generation(self):
        if self.roulette:
            temp_pop = self.roulette_wheel()
        else:
            temp_pop = self.tournament_selection()

        offspring = self.crossover(temp_pop)
        self.mutate(offspring)
        self.evaluate(offspring)

        if self.save:
            self.save_best(self.population, offspring)

        self.population = offspring
        self.generation += 1
        self.write_current_generation()

    def matches_cond(self, condition, example):
        """ Check if a rule matches an example """

        # Compare each bit, return true if all pass
        for i in range(len(example.rule)):
            if condition.rule[i] != '#':
                if condition.rule[i] != example.rule[i]:
                    return False
        return True

    def matches_out(self, condition, example):
        """ Check if an output matches an example """

        if condition.out != example.out:
            return False
        return True

    def fitness_func(self, i):
        """ Calculate fitness of a given genome """

        # 6 bit rules
        fitness = 0
        rules = []

        # Create rules for each set of rules in an individual
        for j in range(0, self.gene_length, self.single_gene_length):
            r = i.genes[j:j+self.rule_length]
            out = i.genes[j+self.rule_length:j+self.single_gene_length]
            rule = Rule(r, out)
            rules.append(rule)

        # Judge fitness by comparing against dataset
        for example in self.dataset:
            rule_count = i.rule_num
            for rule in rules:
                if self.matches_cond(rule, example):
                    if self.matches_out(rule, example):
                        fitness += 1
                    break
                # Compare only the number of rules specified in individual
                rule_count -= 1
                if rule_count == 0:
                    break

        return fitness

    def evaluate(self, pop):
        """ Evaluate a given population """

        best_fitness = 0
        best_rules = self.rules + 1
        total_fitness = 0
        worst_fitness = len(self.dataset)

        for i in pop:
            i.fitness = self.fitness_func(i)
            if i.fitness >= best_fitness :
                if i.fitness > best_fitness :
                    best_fitness = i.fitness
                    best_rules = i.rule_num
                elif i.rule_num < best_rules:
                    best_fitness = i.fitness
                    best_rules = i.rule_num
            if i.fitness < worst_fitness : worst_fitness = i.fitness
            total_fitness += i.fitness

        self.best_rules = best_rules
        self.best_fitness = best_fitness
        self.total_fitness = total_fitness
        self.worst_fitness = worst_fitness

    def save_best(self, pop1, pop2):
        """ Save the best in the initial population and insert to offspring """

        worst = pop2[0]
        best = Individual() # Default 0 fitness
        best.rule_num = self.rules + 1
        # Save best of first populartion

        for i in pop1:
            if i.fitness >= best.fitness :
                if i.fitness > best.fitness :
                    best = i
                elif i.rule_num < best.rule_num :
                    best = i

        for i in pop2:
            if i.fitness <= worst.fitness : worst = i

        pop2.remove(worst)
        pop2.append(best)
        self.best_fitness = best.fitness
        self.best_rules = best.rule_num


    def tournament_selection(self):
        offspring = []

        for i in range(self.size):
            parent1 = random.randint(0, self.size-1)
            parent2 = random.randint(0, self.size-1)
            if self.population[parent1].fitness > self.population[parent2].fitness:
                parent = Individual()
                parent.genes = list(self.population[parent1].genes)
                offspring.append(parent)
            else:
                parent = Individual()
                parent.genes = list(self.population[parent2].genes)
                offspring.append(parent)

        return offspring

    def roulette_wheel(self):
        offspring = []
        total = self.total_fitness

        for i in range(self.size):
            current = 0
            stop_value = random.randint(0, total)
            for j in range(self.size):
                current += self.population[j].fitness
                if current > stop_value:
                    ind = Individual()
                    ind.genes = list(self.population[j].genes)
                    offspring.append(ind)

        return offspring


    # Single point crossover
    def crossover(self, pop):
        offspring = []
        for i in range(self.size):
            if self.crossover_chance > random.random():
                parent1 = random.randint(0, self.size-1)
                parent2 = random.randint(0, self.size-1)
                cross_point = random.randint(0, self.gene_length-1)
                child = Individual()

                # Creates genes by combining 2 cut lists of genes
                new_genes = pop[parent1].genes[:cross_point]
                new_genes.extend(pop[parent2].genes[cross_point:])

                child.genes = new_genes
                child.rule_num = pop[parent2].rule_num
                offspring.append(child)

            else:
                child = random.randint(0,self.size-1)
                offspring.append(pop[child])

        return offspring

    # Bit-wise mutation
    def mutate(self, pop):
        # For each individual
        for i in range(self.size):
            child = pop[i]
            # For each rule in individual
            for j in range(0, self.gene_length, self.single_gene_length):
                # Mutate rule
                for k in range(j, j+self.rule_length):
                    if self.mutate_chance > random.random():
                        # Pick anything from the alphabet except the current value
                        filtered_list = [l for l in gene_alphabet if l != child.genes[k]]
                        child.genes[k] = random.choice(filtered_list)

                # Mutate rule output
                for k in range(j+self.rule_length, j+self.single_gene_length):
                    if self.mutate_chance > random.random():
                        child.genes[k] = 1 - child.genes[k]

                # Mutate rule count
                if self.mutate_chance > random.random():
                    child.rule_num = randint(self.min_rules, self.rules)



    def print_pop(self):
        print("Gen {} - Worst {} - Best {} r{} - Total {} - Mean {}".format(
            self.generation, self.worst_fitness, self.best_fitness, self.best_rules, self.total_fitness, round(self.total_fitness / len(self.population),2)))

if __name__ == "__main__":
    pop = Population()
    pop.setup()
    pop.print_pop()

    # Run G generations
    for i in range(G-1):
        pop.next_generation();
        pop.print_pop();
        if pop.best_fitness == pop.max_fitness:
            if pop.best_rules == pop.min_rules:
                break

    print("Best Individual\n{}".format(pop.get_best(pop.population)))
    pop.end_csv()
