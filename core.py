from graphviz import Digraph

class Token:
	def __init__(self, initializer):
		self.content = initializer

	def __repr__(self):
		return self.__class__.__name__ + '(' + str(self.content) + ')'

	def parse(self):
		raise NotImplementedError('Method parse is not implemented in Token class')

class LetterToken(Token):
	def parse(self):
		return LetterToken(self.content)

class SequenceToken(Token):
	def parse(self):
		if '|' in self.content:
			return DisjunctionToken([SequenceToken(item) for item in self.content.split('|')]).parse()
		else:
			return [LetterToken(item) for item in self.content]

class RegexToken(Token):
	def parse(self):
		return Lexer.tokenize(self.content)

class DisjunctionToken(Token):
	def parse(self):
		return DisjunctionToken([item.parse() for item in self.content])

class GroupToken(Token):
	def parse(self):
		return GroupToken(RegexToken(self.content[1:-1]).parse())

class IterationToken(Token):
	def parse(self):
		return IterationToken(RegexToken(self.content[1:-1]).parse())

class StrongIterationToken(Token):
	def parse(self):
		return StrongIterationToken(RegexToken(self.content[1:-1]).parse())

class Lexer:
	@classmethod
	def __parse_groups(cls, regex):
		current_group = ''
		groups = []
		opened = 0
		opened_curve = 0
		opened_bracket = 0
		for char in regex:
			if char == '(' and opened_curve == 0 and opened_bracket == 0:
				if opened == 0 and len(current_group) > 0:
					groups.append(SequenceToken(current_group))
					current_group = ''
				opened += 1
				current_group += char
			elif char == ')' and opened_curve == 0 and opened_bracket == 0:
				opened -= 1
				if opened < 0:
					raise ValueError('Incorrect regex')
				current_group += char
				if opened == 0:
					groups.append(GroupToken(current_group))
					current_group = ''
			elif char == '{' and opened == 0 and opened_bracket == 0:
				if opened_curve == 0 and len(current_group) > 0:
					groups.append(SequenceToken(current_group))
					current_group = ''
				opened_curve += 1
				current_group += char
			elif char == '}' and opened == 0 and opened_bracket == 0:
				opened_curve -= 1
				if opened_curve < 0:
					raise ValueError('Incorrect regex')
				current_group += char
				if opened_curve == 0:
					groups.append(IterationToken(current_group))
					current_group = ''
			elif char == '[' and opened == 0 and opened_curve == 0:
				if opened_bracket == 0 and len(current_group) > 0:
					groups.append(SequenceToken(current_group))
					current_group = ''
				opened_bracket += 1
				current_group += char
			elif char == ']' and opened == 0 and opened_curve == 0:
				opened_bracket -= 1
				if opened_bracket < 0:
					raise ValueError('Incorrect regex')
				current_group += char
				if opened_bracket == 0:
					groups.append(StrongIterationToken(current_group))
					current_group = ''
			else:
				current_group += char
		if opened > 0 or opened_curve > 0:
			raise ValueError('Incorrect regex')
		if len(current_group) > 0:
			groups.append(SequenceToken(current_group))
		return groups

	@classmethod
	def __outer_parse(cls, groups):
		return [item.parse() for item in groups]

	@classmethod
	def __make_plane(cls, parsed):
		result = []
		for item in parsed:
			if type(item) == type([]):
				result += item
			else:
				result.append(item)
		return result

	@classmethod
	def tokenize(cls, regex):
		return cls.__make_plane(cls.__outer_parse(cls.__parse_groups(regex)))

class FSM:
	EPSILON = '$'

	def __init__(self):
		self.__states = {}
		self.__final_states = []
		self.__current_state = None

	def __copy(self):
		b = FSM()
		b.__states = self.__states
		b.__final_states = self.__final_states
		b.__current_state = self.__current_state
		return b

	def __transition(self, char):
		try:
			ways = self.__states[self.__current_state][char]
			results = [self.__copy() for _ in ways]
			for i in range(len(ways)):
				results[i].__current_state = ways[i]
			return results
		except:
			return []

	def __is_in_final_state(self):
		return self.__current_state in self.__final_states

	def all_possible_transitions(self, states, char):
		result = []
		for state in states:
			try:
				transitions = self.__states[state][char]
				for t in transitions:
					result += self.epsilon_closure(t)
			except:
				pass
			# try:
			# 	result += self.__states[state][FSM.EPSILON]
			# except:
			# 	pass
		result = sorted(list(set(result)))
		return result

	def all_possible_chars(self, states):
		result = []
		for state in states:
			result += self.__states[state].keys()
		result = sorted(list(set(result)))
		return result

	def add_state(self, index, is_final):
		if index in self.__states:
			raise ValueError('State is already exist in FSM')
		else:
			self.__states[index] = {}
			if is_final:
				self.__final_states.append(index)

	def add_transition(self, source, target, char):
		if source in self.__states and target in self.__states:
			try:
				self.__states[source][char].append(target)
			except:
				self.__states[source][char] = [target]
		else:
			raise ValueError('Source or target does not exist in FSM')

	def set_initial_state(self, index):
		if index in self.__states:
			self.__current_state = index
		else:
			raise ValueError('State does not exist in FSM')

	def add_final_state(self, index):
		if index in self.__states:
			self.__final_states.append(index)
		else:
			raise ValueError('State does not exist in FSM')

	def epsilon_closure(self, index):
		result = [index]
		try:
			epsilon_ways = self.__states[index][FSM.EPSILON]
			for way in epsilon_ways:
				result += self.epsilon_closure(way)
		except:
			pass
		return sorted(list(set(result)))

	def all_epsilon_closures(self):
		result = []
		for index in self.__states:
			result.append((index, self.epsilon_closure(index)))
		return result

	def acceptance(self, s):
		if len(s) == 0:
			return self.__is_in_final_state()
		else:
			step = self.__transition(s[0])
			for item in step:
				if item.acceptance(s[1:]):
					return True
			return False

	def get_dot_structure(self):
		dot = Digraph()
		dot.format = 'png'
		dot.attr(rankdir='LR')
		dot.node('', shape='none')
		for state in self.__states:
			if state in self.__final_states:
				dot.node(state, shape='doublecircle')
			else:
				dot.node(state, shape='circle')
		dot.edge('', self.__current_state)
		for state in self.__states:
			for char in self.__states[state]:
				for transition in self.__states[state][char]:
					dot.edge(state, transition, label=char)
		return dot

class FSMBuilder:
	@classmethod
	def build(cls, tokens):
		a = FSM()
		a.add_state('0', False)
		a.add_state('1', True)
		a.add_transition('0', '1', '@0')
		a.set_initial_state('0')
		address = 1
		last_state = 1
		addr = [('@0', tokens, '0', '1')]
		while len(addr) > 0:
			current = addr[0]
			if type(current[1]) == type([]):
				prev = current[2]
				last_in_seq = current[3]
				del a._FSM__states[current[2]][current[0]]
				for i in current[1][:-1]:
					last_state += 1
					a.add_state(str(last_state), False)
					if type(i) == type(LetterToken('')):
						a.add_transition(str(prev), str(last_state), i.content)
					elif type(i) == type(GroupToken('')):
						addr.append(('@' + str(address), i.content, str(prev), str(last_state)))
						a.add_transition(str(prev), str(last_state), '@' + str(address))
						address += 1
					else:
						addr.append(('@' + str(address), i, str(prev), str(last_state)))
						a.add_transition(str(prev), str(last_state), '@' + str(address))
						address += 1
					prev = last_state
				if type(current[1][-1]) == type(LetterToken('')):
					a.add_transition(str(prev), str(last_in_seq), current[1][-1].content)
				elif type(current[1][-1]) == type(GroupToken('')):
					addr.append(('@' + str(address), current[1][-1].content, str(prev), str(last_in_seq)))
					a.add_transition(str(prev), str(last_in_seq), '@' + str(address))
					address += 1
				else:
					addr.append(('@' + str(address), current[1][-1], str(prev), str(last_in_seq)))
					a.add_transition(str(prev), str(last_in_seq), '@' + str(address))
					address += 1
				addr = addr[1:]
			elif type(current[1]) == type(DisjunctionToken('')):
				del a._FSM__states[current[2]][current[0]]
				from_state = current[2]
				to_state = current[3]
				for item in current[1].content:
					addr.append(('@' + str(address), item, from_state, to_state))
					a.add_transition(from_state, to_state, '@' + str(address))
					address += 1
				addr = addr[1:]
			elif type(current[1]) == type(IterationToken('')):
				del a._FSM__states[current[2]][current[0]]
				from_state = current[2]
				to_state = current[3]
				last_state += 1
				a.add_state(str(last_state), False)
				a.add_transition(from_state, str(last_state), FSM.EPSILON)
				a.add_transition(str(last_state), to_state, FSM.EPSILON)
				addr.append(('@' + str(address), current[1].content, str(last_state), str(last_state)))
				a.add_transition(str(last_state), str(last_state), '@' + str(address))
				address += 1
				addr = addr[1:]
			else:
				break
		return a

	@classmethod
	def determinize(cls, fsm):
		def find_key_by_value(d, v):
			for k in d:
				if d[k] == v:
					return k
			return None

		determined = FSM()
		start = fsm.epsilon_closure(fsm._FSM__current_state)
		new_keys = { '0': start }
		queue = ['0']
		new_state_key = 1
		is_final = False
		for item in start:
			if item in fsm._FSM__final_states:
				is_final = True
		determined.add_state(queue[0], is_final)
		determined.set_initial_state(queue[0])
		while len(queue) > 0:
			current = queue[0]
			queue = queue[1:]
			closure = new_keys[current]
			chars = fsm.all_possible_chars(closure)
			if FSM.EPSILON in chars:
				pos = chars.index(FSM.EPSILON)
				chars = chars[:pos] + chars[pos + 1:]
			for char in chars:
				trans = fsm.all_possible_transitions(closure, char)
				to_state = find_key_by_value(new_keys, trans)
				if to_state is None:
					to_state = str(new_state_key)
					new_state_key += 1
					new_keys[to_state] = trans
					queue.append(to_state)
					is_final = False
					for item in trans:
						if item in fsm._FSM__final_states:
							is_final = True
					determined.add_state(to_state, is_final)
				determined.add_transition(current, to_state, char)
		return determined

	@classmethod
	def build_determined(cls, tokens):
		nfa = cls.build(tokens)
		nfa.get_dot_structure().render('nfa.gv', view=False)
		dfa = cls.determinize(nfa)
		dfa.get_dot_structure().render('dfa.gv', view=False)
		return dfa

class MooreMachine:
	EPSILON = '$'

	def __init__(self):
		self.__states = {}
		self.__final_states = []
		self.__current_state = None
		self.__returns = {}

	def __copy(self):
		b = MooreMachine()
		b.__states = self.__states
		b.__final_states = self.__final_states
		b.__current_state = self.__current_state
		b.__returns = self.__returns
		return b

	def __transition(self, char):
		try:
			ways = self.__states[self.__current_state][char]
			results = [self.__copy() for _ in ways]
			for i in range(len(ways)):
				results[i].__current_state = ways[i]
			return results
		except:
			return []

	def __is_in_final_state(self):
		return self.__current_state in self.__final_states

	def all_possible_transitions(self, states, char):
		result = []
		for state in states:
			try:
				transitions = self.__states[state][char]
				for t in transitions:
					result += self.epsilon_closure(t)
			except:
				pass
		result = sorted(list(set(result)))
		return result

	def all_possible_chars(self, states):
		result = []
		for state in states:
			result += self.__states[state].keys()
		result = sorted(list(set(result)))
		return result

	def add_state(self, index, return_list, is_final):
		if index in self.__states:
			raise ValueError('State is already exist in MooreMachine')
		else:
			self.__states[index] = {}
			self.__returns[index] = return_list
			if is_final:
				self.__final_states.append(index)

	def add_transition(self, source, target, char):
		if source in self.__states and target in self.__states:
			try:
				self.__states[source][char].append(target)
			except:
				self.__states[source][char] = [target]
		else:
			raise ValueError('Source or target does not exist in MooreMachine')

	def set_initial_state(self, index):
		if index in self.__states:
			self.__current_state = index
		else:
			raise ValueError('State does not exist in MooreMachine')

	def add_final_state(self, index):
		if index in self.__states:
			self.__final_states.append(index)
		else:
			raise ValueError('State does not exist in MooreMachine')

	def epsilon_closure(self, index):
		result = [index]
		try:
			epsilon_ways = self.__states[index][MooreMachine.EPSILON]
			for way in epsilon_ways:
				result += self.epsilon_closure(way)
		except:
			pass
		return sorted(list(set(result)))

	def all_epsilon_closures(self):
		result = []
		for index in self.__states:
			result.append((index, self.epsilon_closure(index)))
		return result

	def acceptance(self, s):
		prev_state = self.__current_state
		if len(s) == 0:
			result = self.__returns[self.__current_state]
			self.__current_state = prev_state
			return result
		else:
			new_start = self.__transition(s[0])
			print(new_start)
			if len(new_start) == 0:
				self.__current_state = prev_state
				return 'None'
			else:
				self.set_initial_state(new_start[0].__current_state)
				result = self.acceptance(s[1:])
				self.__current_state = prev_state
				return result

	def get_dot_structure(self):
		dot = Digraph()
		dot.format = 'png'
		dot.attr(rankdir='LR')
		dot.node('', shape='none')
		for state in self.__states:
			if state in self.__final_states:
				dot.node(state + ' - ' + str(self.__returns[state]), shape='doublecircle')
			else:
				dot.node(state + ' - ' + str(self.__returns[state]), shape='circle')
		dot.edge('', self.__current_state + ' - ' + str(self.__returns[self.__current_state]))
		for state in self.__states:
			for char in self.__states[state]:
				for transition in self.__states[state][char]:
					dot.edge(state + ' - ' + str(self.__returns[state]), transition + ' - ' + str(self.__returns[transition]), label=char)
		return dot

class MooreMachineBuilder:
	@classmethod
	def build(cls, tokens_lists):
		a = MooreMachine()
		a.add_state('0', None, False)
		last_state = 0
		addr = []
		a.set_initial_state('0')
		for tokens in tokens_lists:
			last_state += 1
			a.add_state(str(last_state), 'R' + str(last_state), True)
			a.add_transition('0', str(last_state), '@' + str(last_state - 1))
			addr.append(('@' + str(last_state - 1), tokens, '0', str(last_state)))
		address = len(addr)
		while len(addr) > 0:
			current = addr[0]
			if type(current[1]) == type([]):
				prev = current[2]
				last_in_seq = current[3]
				del a._MooreMachine__states[current[2]][current[0]]
				for i in current[1][:-1]:
					last_state += 1
					a.add_state(str(last_state), None, False)
					if type(i) == type(LetterToken('')):
						a.add_transition(str(prev), str(last_state), i.content)
					elif type(i) == type(GroupToken('')):
						addr.append(('@' + str(address), i.content, str(prev), str(last_state)))
						a.add_transition(str(prev), str(last_state), '@' + str(address))
						address += 1
					else:
						addr.append(('@' + str(address), i, str(prev), str(last_state)))
						a.add_transition(str(prev), str(last_state), '@' + str(address))
						address += 1
					prev = last_state
				if type(current[1][-1]) == type(LetterToken('')):
					a.add_transition(str(prev), str(last_in_seq), current[1][-1].content)
				elif type(current[1][-1]) == type(GroupToken('')):
					addr.append(('@' + str(address), current[1][-1].content, str(prev), str(last_in_seq)))
					a.add_transition(str(prev), str(last_in_seq), '@' + str(address))
					address += 1
				else:
					addr.append(('@' + str(address), current[1][-1], str(prev), str(last_in_seq)))
					a.add_transition(str(prev), str(last_in_seq), '@' + str(address))
					address += 1
				addr = addr[1:]
			elif type(current[1]) == type(DisjunctionToken('')):
				del a._MooreMachine__states[current[2]][current[0]]
				from_state = current[2]
				to_state = current[3]
				for item in current[1].content:
					addr.append(('@' + str(address), item, from_state, to_state))
					a.add_transition(from_state, to_state, '@' + str(address))
					address += 1
				addr = addr[1:]
			elif type(current[1]) == type(IterationToken('')):
				del a._MooreMachine__states[current[2]][current[0]]
				from_state = current[2]
				to_state = current[3]
				last_state += 1
				a.add_state(str(last_state), None, False)
				a.add_transition(from_state, str(last_state), MooreMachine.EPSILON)
				a.add_transition(str(last_state), to_state, MooreMachine.EPSILON)
				addr.append(('@' + str(address), current[1].content, str(last_state), str(last_state)))
				a.add_transition(str(last_state), str(last_state), '@' + str(address))
				address += 1
				addr = addr[1:]
			else:
				break
		return a

	@classmethod
	def determinize(cls, moore_machine):
		def find_key_by_value(d, v):
			for k in d:
				if d[k] == v:
					return k
			return None

		determined = MooreMachine()
		start = moore_machine.epsilon_closure(moore_machine._MooreMachine__current_state)
		new_keys = { '0': start }
		queue = ['0']
		new_state_key = 1
		is_final = False
		mark = None
		for item in start:
			if item in moore_machine._MooreMachine__final_states:
				is_final = True
				if mark is None:
					mark = [moore_machine._MooreMachine__returns[item]]
				else:
					mark.append(moore_machine._MooreMachine__returns[item])
		determined.add_state(queue[0], mark, is_final)
		determined.set_initial_state(queue[0])
		while len(queue) > 0:
			current = queue[0]
			queue = queue[1:]
			closure = new_keys[current]
			chars = moore_machine.all_possible_chars(closure)
			if MooreMachine.EPSILON in chars:
				pos = chars.index(MooreMachine.EPSILON)
				chars = chars[:pos] + chars[pos + 1:]
			for char in chars:
				trans = moore_machine.all_possible_transitions(closure, char)
				to_state = find_key_by_value(new_keys, trans)
				if to_state is None:
					to_state = str(new_state_key)
					new_state_key += 1
					new_keys[to_state] = trans
					queue.append(to_state)
					is_final = False
					mark = None
					for item in trans:
						if item in moore_machine._MooreMachine__final_states:
							is_final = True
							if mark is None:
								mark = [moore_machine._MooreMachine__returns[item]]
							else:
								mark.append(moore_machine._MooreMachine__returns[item])
					determined.add_state(to_state, mark, is_final)
				determined.add_transition(current, to_state, char)
		return determined

	@classmethod
	def build_moore(cls, tokens_lists):
		nfa = cls.build(tokens_lists)
		nfa.get_dot_structure().render('nfa.gv', view=False)
		dfa = cls.determinize(nfa)
		dfa.get_dot_structure().render('dfa.gv', view=False)
		return dfa

class BuchiMachine:
	EPSILON = '$'

	def __init__(self):
		self.__states = {}
		self.__final_states = []
		self.__current_state = None
		self.__returns = {}

	def __copy(self):
		b = BuchiMachine()
		b.__states = self.__states
		b.__final_states = self.__final_states
		b.__current_state = self.__current_state
		b.__returns = self.__returns
		return b

	def __transition(self, char):
		try:
			ways = self.__states[self.__current_state][char]
			results = [self.__copy() for _ in ways]
			for i in range(len(ways)):
				results[i].__current_state = ways[i]
			return results
		except:
			return []

	def __is_in_final_state(self):
		return self.__current_state in self.__final_states

	def all_possible_transitions(self, states, char):
		result = []
		for state in states:
			try:
				transitions = self.__states[state][char]
				for t in transitions:
					result += self.epsilon_closure(t)
			except:
				pass
		result = sorted(list(set(result)))
		return result

	def all_possible_chars(self, states):
		result = []
		for state in states:
			result += self.__states[state].keys()
		result = sorted(list(set(result)))
		return result

	def add_state(self, index, return_list, is_final):
		if index in self.__states:
			raise ValueError('State is already exist in BuchiMachine')
		else:
			self.__states[index] = {}
			self.__returns[index] = return_list
			if is_final:
				self.__final_states.append(index)

	def add_transition(self, source, target, char):
		if source in self.__states and target in self.__states:
			try:
				self.__states[source][char].append(target)
			except:
				self.__states[source][char] = [target]
		else:
			raise ValueError('Source or target does not exist in BuchiMachine')

	def set_initial_state(self, index):
		if index in self.__states:
			self.__current_state = index
		else:
			raise ValueError('State does not exist in BuchiMachine')

	def add_final_state(self, index):
		if index in self.__states:
			self.__final_states.append(index)
		else:
			raise ValueError('State does not exist in BuchiMachine')

	def merge_states(self, from_state, to_state):
		print('MERGE FROM %s TO %s' % (from_state, to_state))
		for state in self.__states:
			for char in self.__states[state]:
				if from_state in self.__states[state][char]:
					if to_state in self.__states[state][char]:
						self.__states[state][char].remove(from_state)
					else:
						self.__states[state][char][self.__states[state][char].index(from_state)] = to_state
		for char in self.__states[from_state]:
			if char in self.__states[to_state]:
				self.__states[to_state][char] += self.__states[from_state][char]
				self.__states[to_state][char] = list(set(self.__states[to_state][char]))
			else:
				self.__states[to_state][char] = self.__states[from_state][char]
		if from_state in self.__final_states:
			if not to_state in self.__final_states:
				self.add_final_state(to_state)
			self.__final_states.remove(from_state)
		del self.__states[from_state]

	def epsilon_closure(self, index):
		result = [index]
		try:
			epsilon_ways = self.__states[index][BuchiMachine.EPSILON]
			for way in epsilon_ways:
				result += self.epsilon_closure(way)
		except:
			pass
		return sorted(list(set(result)))

	def all_epsilon_closures(self):
		result = []
		for index in self.__states:
			result.append((index, self.epsilon_closure(index)))
		return result

	def acceptance(self, s):
		prev_state = self.__current_state
		if len(s) == 0:
			result = self.__returns[self.__current_state]
			self.__current_state = prev_state
			return result
		else:
			new_start = self.__transition(s[0])
			print(new_start)
			if len(new_start) == 0:
				self.__current_state = prev_state
				return 'None'
			else:
				self.set_initial_state(new_start[0].__current_state)
				result = self.acceptance(s[1:])
				self.__current_state = prev_state
				return result

	def get_dot_structure(self):
		dot = Digraph()
		dot.format = 'png'
		dot.attr(rankdir='LR')
		dot.node('', shape='none')
		for state in self.__states:
			if state in self.__final_states:
				dot.node(state, shape='doublecircle')
			else:
				dot.node(state, shape='circle')
		dot.edge('', self.__current_state)
		for state in self.__states:
			for char in self.__states[state]:
				for transition in self.__states[state][char]:
					dot.edge(state, transition, label=char)
		return dot

class BuchiMachineBuilder:
	@classmethod
	def build(cls, tokens_lists):
		a = BuchiMachine()
		a.add_state('0', None, False)
		last_state = 0
		addr = []
		a.set_initial_state('0')
		for tokens in tokens_lists:
			last_state += 1
			a.add_state(str(last_state), 'R' + str(last_state), True)
			a.add_transition('0', str(last_state), '@' + str(last_state - 1))
			addr.append(('@' + str(last_state - 1), tokens, '0', str(last_state)))
		address = len(addr)
		while len(addr) > 0:
			current = addr[0]
			if type(current[1]) == type([]):
				prev = current[2]
				last_in_seq = current[3]
				del a._BuchiMachine__states[current[2]][current[0]]
				for i in current[1][:-1]:
					last_state += 1
					a.add_state(str(last_state), None, False)
					if type(i) == type(LetterToken('')):
						a.add_transition(str(prev), str(last_state), i.content)
					elif type(i) == type(GroupToken('')):
						addr.append(('@' + str(address), i.content, str(prev), str(last_state)))
						a.add_transition(str(prev), str(last_state), '@' + str(address))
						address += 1
					else:
						addr.append(('@' + str(address), i, str(prev), str(last_state)))
						a.add_transition(str(prev), str(last_state), '@' + str(address))
						address += 1
					prev = last_state
				if type(current[1][-1]) == type(LetterToken('')):
					a.add_transition(str(prev), str(last_in_seq), current[1][-1].content)
				elif type(current[1][-1]) == type(GroupToken('')):
					addr.append(('@' + str(address), current[1][-1].content, str(prev), str(last_in_seq)))
					a.add_transition(str(prev), str(last_in_seq), '@' + str(address))
					address += 1
				else:
					addr.append(('@' + str(address), current[1][-1], str(prev), str(last_in_seq)))
					a.add_transition(str(prev), str(last_in_seq), '@' + str(address))
					address += 1
				addr = addr[1:]
			elif type(current[1]) == type(DisjunctionToken('')):
				del a._BuchiMachine__states[current[2]][current[0]]
				from_state = current[2]
				to_state = current[3]
				for item in current[1].content:
					addr.append(('@' + str(address), item, from_state, to_state))
					a.add_transition(from_state, to_state, '@' + str(address))
					address += 1
				addr = addr[1:]
			elif type(current[1]) == type(IterationToken('')):
				del a._BuchiMachine__states[current[2]][current[0]]
				from_state = current[2]
				to_state = current[3]
				last_state += 1
				a.add_state(str(last_state), None, False)
				a.add_transition(from_state, str(last_state), BuchiMachine.EPSILON)
				a.add_transition(str(last_state), to_state, BuchiMachine.EPSILON)
				addr.append(('@' + str(address), current[1].content, str(last_state), str(last_state)))
				a.add_transition(str(last_state), str(last_state), '@' + str(address))
				address += 1
				addr = addr[1:]
			elif type(current[1]) == type(StrongIterationToken('')):
				del a._BuchiMachine__states[current[2]][current[0]]
				from_state = current[2]
				to_state = current[3]
				a.add_transition(from_state, to_state, '@' + str(address))
				addr.append(('@' + str(address), current[1].content, from_state, from_state))
				a.merge_states(to_state=from_state, from_state=to_state)
				address += 1
				addr = addr[1:]
			else:
				break
		return a

	@classmethod
	def determinize(cls, buchi_machine):
		def find_key_by_value(d, v):
			for k in d:
				if d[k] == v:
					return k
			return None

		determined = BuchiMachine()
		start = buchi_machine.epsilon_closure(buchi_machine._BuchiMachine__current_state)
		new_keys = { '0': start }
		queue = ['0']
		new_state_key = 1
		is_final = False
		mark = None
		for item in start:
			if item in buchi_machine._BuchiMachine__final_states:
				is_final = True
				if mark is None:
					mark = [buchi_machine._BuchiMachine__returns[item]]
				else:
					mark.append(buchi_machine._BuchiMachine__returns[item])
		determined.add_state(queue[0], mark, is_final)
		determined.set_initial_state(queue[0])
		while len(queue) > 0:
			current = queue[0]
			queue = queue[1:]
			closure = new_keys[current]
			chars = buchi_machine.all_possible_chars(closure)
			if BuchiMachine.EPSILON in chars:
				pos = chars.index(BuchiMachine.EPSILON)
				chars = chars[:pos] + chars[pos + 1:]
			for char in chars:
				trans = buchi_machine.all_possible_transitions(closure, char)
				to_state = find_key_by_value(new_keys, trans)
				if to_state is None:
					to_state = str(new_state_key)
					new_state_key += 1
					new_keys[to_state] = trans
					queue.append(to_state)
					is_final = False
					mark = None
					for item in trans:
						if item in buchi_machine._BuchiMachine__final_states:
							is_final = True
							if mark is None:
								mark = [buchi_machine._BuchiMachine__returns[item]]
							else:
								mark.append(buchi_machine._BuchiMachine__returns[item])
					determined.add_state(to_state, mark, is_final)
				determined.add_transition(current, to_state, char)
		return determined

	@classmethod
	def build_buchi(cls, tokens_lists):
		nfa = cls.build(tokens_lists)
		print(nfa._BuchiMachine__states)
		nfa.get_dot_structure().render('nfa.gv', view=False)
		dfa = cls.determinize(nfa)
		dfa.get_dot_structure().render('dfa.gv', view=False)
		return dfa

