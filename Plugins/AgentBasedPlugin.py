import sys
sys.path.append('../')

import environment



class AgentBasedPlugin(environment.TimeActionPlugin):
    '''
    Adds TimeActions to model simplified desire and trading behavior.

            set_desire
                defines the desire of a node
                    Params:
                        region : region of the node
                        node : node to set desire
                        population_template : template desired
                        quantity : quantity desired

            propose_trade
                proposes a trade with other nodes
                    Params:
                        region : region of the node
                        node : node to propose trade
                        offer_population_template: the characteristic offered
                        offer_quantity : quantity offered
                        request_population_template: the characteristic offered
                        request_quantity : quantity requested
    '''

    def __init__(self, env_graph):
        super().__init__()
        self.env_graph = env_graph

        environment.TimeActionPlugin.set_pair(self,'set_desire', self.set_desire)
        environment.TimeActionPlugin.set_pair(self, 'propose_trade', self.propose_trade)
        self.env_graph.base_actions.add('set_desire')

    ## Base. Will be broken up into smaller actions
    def set_desire(self, values):
        ## TODO Incomplete. Should converge to node
        #print('converge Values: \n', values, '\n\n')
        target_region = values['region']
        if isinstance(target_region, str):
            target_region = self.env_graph.get_region_by_name(values['region'])

        node = values['node']
        if isinstance(node, str):
            node = target_region.get_node_by_name(node)

        pop_template = values['population_template']
        quantity = values['quantity']
        node.set_desire(quantity, pop_template)


        ## Complex time action. Will be broken up into smaller actions
    def propose_trade(self, values):
        ## TODO Incomplete. Should converge to node
        #print('converge Values: \n', values, '\n\n')
        target_region = values['region']
        if isinstance(target_region, str):
            target_region = self.env_graph.get_region_by_name(values['region'])

        node = values['node']
        if isinstance(node, str):
            node = target_region.get_node_by_name(node)

        offer_quantity = values['offer_quantity']
        offer_pop_template = values['offer_population_template']

        request_quantity = values['request_quantity']
        request_pop_template = values['request_population_template']

        trade_done = False
        action_list = []
        for region in self.env_graph.region_list:
            for other_node in region.node_list:

                if other_node.id == node.id:
                    continue 
                
                if trade_done:
                    continue

                offer_response = other_node.evaluate_offer( offer_quantity,
                                                            offer_pop_template, 
                                                            request_quantity,
                                                            request_pop_template)
                                                        
                if offer_response:
                    print(offer_response)
                    print(target_region.name, node.name, region.name, other_node.name)
                    trade_done = True
                    desire_quantity, desire_template = node.desire
                    node.desire = (desire_quantity - request_quantity, desire_template)
                    
                    request_action_values = {}
                    request_action_type = 'move_population'
                    request_action_values['origin_region'] = target_region.name
                    request_action_values['origin_node'] = node.name
                    request_action_values['destination_region'] = region.name
                    request_action_values['destination_node'] = other_node.name
                    request_action_values['quantity'] = request_quantity
                    request_action_values['population_template'] = request_pop_template
                    request_action = environment.TimeAction(_type = request_action_type, _values = request_action_values)
                    
                    send_action_values = {}
                    send_action_type = 'move_population'
                    send_action_values['origin_region'] = region.name
                    send_action_values['origin_node'] = other_node.name
                    send_action_values['destination_region'] = target_region.name
                    send_action_values['destination_node'] = node.name
                    send_action_values['quantity'] = offer_quantity
                    send_action_values['population_template'] = offer_pop_template
                    send_action = environment.TimeAction(_type = send_action_type, _values = send_action_values)
                    
                    action_list.append(send_action)
                    action_list.append(request_action)

        return action_list
