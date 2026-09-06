module spi_p(
    input data,
    input lowSelect,
    input clk,
    input sclk,
    input rst_n,
    output reg [7:0] en_reg_out_7_0,
    output reg [7:0] en_reg_out_15_8,
    output reg [7:0] en_reg_pwm_7_0,
    output reg [7:0] en_reg_pwm_15_8,
    output reg [7:0] pwm_duty_cycle


);
localparam MAX_ADDRESS       = 7'd4;
localparam   state_error=2'b11,
            state_sample_addr = 2'b01,
            state_sample_data = 2'b10;
reg [1:0] current_state;
reg [14:0] data_stored;

reg [2:0] bit_count;

reg  data_sync;
reg  cs_sync;
reg [1:0] sclk_sync;

reg transaction_ready;

wire sclk_rising_edge = (sclk_sync == 2'b01);



always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        data_sync <= 1'b0;
        cs_sync   <= 1'b1; // Active low CS defaults HIGH
        sclk_sync <= 2'b0;
    end else begin
        data_sync <=  data;
        cs_sync   <= lowSelect;
        sclk_sync <= {sclk_sync[0], sclk};
    end

end

always @(posedge clk or negedge rst_n) begin
   

    if(!rst_n) begin
        current_state <= state_sample_addr;
        bit_count<=3'd0;
        data_stored<=15'b0;
        en_reg_out_7_0<=8'b0;
        en_reg_out_15_8<=8'b0;
        en_reg_pwm_7_0<=8'b0;
        en_reg_pwm_15_8<=8'b0;
        pwm_duty_cycle<=8'b0;
        transaction_ready <= 1'b0;
    end else if (cs_sync) begin

        if (transaction_ready) begin
                case (data_stored[14:8])
                    7'd0: en_reg_out_7_0  <= data_stored[7:0];
                    7'd1: en_reg_out_15_8 <= data_stored[7:0];
                    7'd2: en_reg_pwm_7_0  <= data_stored[7:0];
                    7'd3: en_reg_pwm_15_8 <= data_stored[7:0];
                    7'd4: pwm_duty_cycle  <= data_stored[7:0];
                    default: ;
                endcase
        end
        current_state <= state_sample_addr;
        bit_count<=3'd0;
        data_stored<=15'b0;
        transaction_ready <= 1'b0;
    end else begin
        case (current_state)
            state_sample_addr: begin
                if(sclk_rising_edge) begin 
                    data_stored <= {data_stored[13:0],data_sync};
                    if(bit_count== 3'b0 && data_sync==1'b0) begin
                        current_state <= state_error;
                    end else if(bit_count==3'd7) begin
                        
                        if({data_stored[5:0],data_sync}>MAX_ADDRESS) begin
                            current_state <= state_error;
                        end else begin
                            current_state <= state_sample_data;
                            bit_count <= 3'b0;
                        end
                    end else begin
                        
                        bit_count <= bit_count + 3'b1;
                    end
                end
            end
            state_sample_data: begin
                if(sclk_rising_edge) begin
                    data_stored <= {data_stored[13:0],data_sync};
                    if(bit_count==3'd7) begin
                        current_state<=state_sample_addr;
                        transaction_ready<=1'b1;
                    end else begin
                        bit_count <= bit_count + 3'd1;
                    end
                end
            end
            state_error: begin
            end
            default:current_state<=state_sample_addr;
        endcase
    end




end
    
    






endmodule