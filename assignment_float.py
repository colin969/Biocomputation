import random
from random import randint
import sys
import os
import math
import re
import time
import csv

# VARIABLES #
P = 500 # Population Size
N = 10 # Number of Rules
N_min = 5 # Minimum number of Rules
G = 1000 # Number of Generations
m_chance = 0.015 # Decimal % chance of mutation
c_chance = 0.98 # Decimal % chance of crossover
roulette = False # Toggle Roulette Wheel selection instead of Tournament selection
save = True # Save best of a population before next population
file_name = "data3.txt" # File containing example data

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
                # Random float in rules, random 0/1 in output
                for j in range(rule_length):
                    genes.append(random.random())
                for j in range(output_length):
                    genes.append(random.choice([0,1]))
            self.genes = genes
        else:
            self.genes = []

        # Initial rule count to consider in fitness
        self.rule_num = randint(min_rules,rules)

        self.fitness = 0
        self.full_fitness = 0

    def __str__(self):
        return "Gene {} - Fitness {}".format(self.genes, self.fitness)

class Population:
    def setup(self, size=P, rules=N, min_rules=N_min, mutate_chance=m_chance,
                crossover_chance=c_chance, roulette=roulette, save=save, dataset=file_name):
        self.roulette = roulette
        self.size = size
        self.rules = rules
        self.min_rules = min_rules
        self.mutate_chance = mutate_chance
        self.crossover_chance = crossover_chance
        self.save = save
        self.generation = 1

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

        self.write_current_generation()

    def start_csv(self):
        timestr = time.strftime("%Y%m%d-%H%M%S")
        headers = ["Generation", "Best", "Total", "Mean", "Best Full"]
        filestr = "{}_C{}_M{}_{}.csv".format(file_name.split(".")[0], str(self.crossover_chance * 100), str(self.mutate_chance * 100), timestr)
        self.open_file = open(filestr, "w", newline='')
        writer = csv.writer(self.open_file)
        writer.writerow(headers)
        self.writer = writer

    def end_csv(self):
        self.open_file.close()

    def write_current_generation(self):
        if(self.generation % 10 == 0):
            self.writer.writerow([self.generation, self.best_fitness, self.total_fitness, round(self.total_fitness / len(self.population), 2), self.best_full_fitness])
        else:
            self.writer.writerow([self.generation, self.best_fitness, self.total_fitness, round(self.total_fitness / len(self.population), 2)])


    def load_data(self, dataset=file_name):
        dset = []
        with open(dataset) as f:
            content = f.readlines()

            # Pull rule and output length via split of first line
            self.rule_length = len(content[1].split(" ")[:-1])
            self.var_length = len(content[1].split(" ")[0])
            self.out_length = len(content[1].split(" ")[-1]) - 1
            print("Rule Length of {} loaded from dataset".format(self.rule_length))
            print("Output Length of {} loaded from dataset".format(self.out_length))

            # Load in every rule
            for i in content[1:]:
                # E.G 01110 becomes [0,1,1,1,0]
                float_list = []
                # Read rule
                for j in i.split(" ")[:-1]:
                    float_list.append(float(j))
                rule = list(float_list)
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

        print("Data Loaded - {} Examples".format(len(dset)))
        self.max_fitness = len(dset)
        self.dataset = dset
        # Double rule length to account for comparison range
        self.rule_length *= 2

    def get_best(self, pop):
        best = pop[0]

        for i in pop:
            if i.fitness > best.fitness:
                best = i

        return best

    def next_generation(self):
        self.generation += 1
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
        self.write_current_generation()

    def matches_cond(self, condition, example):
        """ Check if a rule matches an example """

        # Compare as a range - E.G Example rule bit 0 is between Condition rule bit 0 and 1, 1 between 2 and 3, etc.
        for i in range(len(example.rule)):
            if(example.rule[i] > condition.rule[i*2]):
                if(example.rule[i] < condition.rule[(i*2)+1]):
                    pass
                else:
                    return False
            else:
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
        full_fitness = 0
        rules = []

        # Create rules for each set of rules in an individual
        for j in range(0, self.gene_length, self.single_gene_length):
            r = i.genes[j:j+self.rule_length]
            out = i.genes[j+self.rule_length:j+self.single_gene_length]
            rule = Rule(r, out)
            rules.append(rule)

        # Judge fitness by comparing against half the dataset
        for example in range(int(len(self.dataset) / 2)):
            for rule in range(len(rules)):
                if self.matches_cond(rules[rule], self.dataset[example]):
                    if self.matches_out(rules[rule], self.dataset[example]):
                        fitness += 1
                    break

        # Every 10th generation run against full data set as well to judge overfit
        if (self.generation % 10 == 0):
            for example in range(int(len(self.dataset))):
                for rule in range(len(rules)):
                    if self.matches_cond(rules[rule], self.dataset[example]):
                        if self.matches_out(rules[rule], self.dataset[example]):
                            full_fitness += 1
                        break

        i.full_fitness = full_fitness
        i.fitness = fitness

    def evaluate(self, pop):
        """ Evaluate a given population """

        best_fitness = 0
        best_full_fitness = 0
        best_rules = self.rules + 1
        total_fitness = 0

        for i in pop:
            self.fitness_func(i)
            if i.fitness >= best_fitness :
                if i.fitness > best_fitness :
                    best_full_fitness = i.full_fitness
                    best_fitness = i.fitness
                    best_rules = i.rule_num
                elif i.rule_num < best_rules:
                    best_full_fitness = i.full_fitness
                    best_fitness = i.fitness
                    best_rules = i.rule_num
            total_fitness += i.fitness

        self.best_rules = best_rules
        self.best_full_fitness = best_full_fitness
        self.best_fitness = best_fitness
        self.total_fitness = total_fitness

    def save_best(self, pop1, pop2):
        """ Save the best in the initial population and insert to offspring """

        worst = pop2[0]
        best = Individual() # Default 0 fitness
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
        total = sum(i.fitness for i in self.population)

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
                        original = child.genes[k]
                        change = random.choice([-0.1, 0.1])
                        new_val = original + change
                        if new_val > 1 or new_val < 0:
                            child.genes[k] = math.floor(abs(new_val))
                        else:
                            child.genes[k] = new_val

                # Mutate rule output
                for k in range(j+self.rule_length, j+self.single_gene_length):
                    if self.mutate_chance > random.random():
                        child.genes[k] = 1 - child.genes[k]

                # Mutate rule count
                if self.mutate_chance > random.random():
                    child.rule_num = randint(self.min_rules, self.rules)


    def print_pop(self):
        if(self.generation % 10 == 0):
            print("Gen {} - Best {} r{} - Best Full {} - Total {} - Mean {}".format(
                self.generation, self.best_fitness, self.best_rules, self.best_full_fitness, self.total_fitness, round(self.total_fitness / len(self.population),2)))
        else:
            print("Gen {} - Best {} r{} - Total {} - Mean {}".format(
                self.generation, self.best_fitness, self.best_rules, self.total_fitness, round(self.total_fitness / len(self.population),2)))

if __name__ == "__main__":
    pop = Population()
    pop.setup()
    pop.print_pop()

    # Run G generations
    for i in range(G-1):
        pop.next_generation();
        pop.print_pop();
        if(pop.max_fitness == pop.best_fitness):
            print("Found 100% Individual!")
            break;
    print("Best Individual\n{}".format(pop.get_best(pop.population)))
