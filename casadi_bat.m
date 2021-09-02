classdef casadi_bat < matlab.System & matlab.system.mixin.Propagates
    % Simulate a li-ion battery with pybamm
    %
    % This template includes the minimum set of functions required
    % to define a System object with discrete state.

    % Public, tunable properties
    
    properties
        %
    end

    properties(DiscreteState)
        %
    end

    % Pre-computed constants
    properties(Access = private)
        y0
        f
        variables
        first_step
    end
    
    methods(Access = protected)
        function num = getNumInputsImpl(~)
            num = 3;
        end
        function num = getNumOutputsImpl(~)
            num = 5;
        end
        function [dt1, dt2, dt3, dt4, dt5] = getOutputDataTypeImpl(~)
        	dt1 = 'double';
            dt2 = 'double';
            dt3 = 'double';
            dt4 = 'double';
            dt5 = 'double';

        end
        function [dt1, dt2, dt3] = getInputDataTypeImpl(~)
        	dt1 = 'double';
            dt2 = 'double';
            dt3 = 'double';
        end
        function [sz1, sz2, sz3, sz4, sz5] = getOutputSizeImpl(~)
        	sz1 = 1;
            sz2 = 1;
            sz3 = 1;
            sz4 = 1;
            sz5 = 1;

        end
        function [sz1, sz2, sz3] = getInputSizeImpl(~)
        	sz1 = 1;
            sz2 = 1;
            sz3 = 1;
        end
        function [cp1, cp2, cp3] = isInputComplexImpl(~)
        	cp1 = false;
            cp2 = false;
            cp3 = false;
        end
        function [cp1, cp2, cp3, cp4, cp5] = isOutputComplexImpl(~)
        	cp1 = false;
            cp2 = false;
            cp3 = false;
            cp4 = false;
            cp5 = false;
        end
        function [fz1, fz2, fz3] = isInputFixedSizeImpl(~)
        	fz1 = true;
            fz2 = true;
            fz3 = true;
        end
        function [fz1, fz2, fz3, fz4, fz5] = isOutputFixedSizeImpl(~)
        	fz1 = true;
            fz2 = true;
            fz3 = true;
            fz4 = true;
            fz5 = true;
        end
        function setupImpl(obj)
            % Perform one-time calculations, such as computing constants
            import casadi.*
            %tmp = load('temp\y0.mat');
            %obj.y0 = inf;
            obj.f = Function.load('temp\integrator.casadi');
            obj.variables = Function.load('temp\variables.casadi');
            obj.first_step = true;
        end

        function [ocp, internal_resistance, heating, neg_conc, pos_conc] = stepImpl(obj, current, temperature, soc_init)
            % Implement algorithm. Calculate y as a function of input u and
            % discrete states.
            if obj.first_step
                if soc_init == 1.0
                    tmp_top = load('temp\y0_top.mat');              
                    obj.y0 = tmp_top.y0;
                else
                    tmp_bot = load('temp\y0_bot.mat');
                    obj.y0 = tmp_bot.y0;
                end
                obj.first_step = false;
            end
            T_ref = 298.15;
            Delta_T = 1.0;
            t_non_dim = (temperature - T_ref) / Delta_T;
            t_min = 1e-6;
            inputs = [t_non_dim, current];
            yt = obj.f(obj.y0, horzcat(inputs, t_min), 0, 0, 0, 0);
            obj.y0 = yt(:, end);
            temp = double(full(obj.variables(0, obj.y0, 0, inputs)));
            v = temp(1);
            ocp = temp(2);
            heating = temp(3);
            neg_conc = temp(4);
            pos_conc = temp(5);
            internal_resistance = abs((ocp - v)/current);
        end

        function resetImpl(obj)
            % Initialize / reset discrete-state properties
        end
    end
end