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
localparam state_idle = 2'b00,
            state_error=2'b11,
            state_sample_addr = 2'b01,
            state_sample_data = 2'b10;
reg [1:0] current_state;
reg [7:0] data_out;
reg [7:0] data_addr;
reg [2:0] addr_bit_count, data_bit_count;

reg [1:0] data_sync;
reg [1:0] cs_sync;
reg [2:0] sclk_sync;

reg transaction_ready;

wire sclk_rising_edge = (sclk_sync[2:1] == 2'b01);
wire sync_cs          = cs_sync[1];
wire sync_data        = data_sync[1];


always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        data_sync <= 2'b0;
        cs_sync   <= 2'b11; // Active low CS defaults HIGH
        sclk_sync <= 3'b0;
    end else begin
        data_sync <= {data_sync[0], data};
        cs_sync   <= {cs_sync[0], lowSelect};
        sclk_sync <= {sclk_sync[1:0], sclk};
    end

end

always @(posedge clk or negedge rst_n) begin
   

    if(!rst_n) begin
        current_state <= state_idle;
        addr_bit_count<=3'd0;
        data_bit_count<=3'd0;
        data_out<=8'b0;
        en_reg_out_7_0<=8'b0;
        en_reg_out_15_8<=8'b0;
        en_reg_pwm_7_0<=8'b0;
        en_reg_pwm_15_8<=8'b0;
        pwm_duty_cycle<=8'b0;
        transaction_ready <= 1'b0;
    end else if (sync_cs) begin

        if (transaction_ready) begin
                case (data_addr[6:0])
                    7'd0: en_reg_out_7_0  <= data_out;
                    7'd1: en_reg_out_15_8 <= data_out;
                    7'd2: en_reg_pwm_7_0  <= data_out;
                    7'd3: en_reg_pwm_15_8 <= data_out;
                    7'd4: pwm_duty_cycle  <= data_out;
                    default: ;
                endcase
        end
        current_state <= state_idle;
        addr_bit_count<=3'd0;
        data_bit_count<=3'd0;
        data_out<=8'b0;
        transaction_ready <= 1'b0;
    end else begin
        case (current_state)
            state_idle: begin
                if (sclk_rising_edge) begin
                    current_state <= state_sample_addr;
                    data_addr <= {7'b0, sync_data};
                    data_out <= 8'b0;
                    addr_bit_count <= 3'd1;
                    data_bit_count <= 3'd0;
                    data_out       <= 8'b0;
                end
            end
            state_sample_addr: begin
                if(sclk_rising_edge) begin 
                    data_addr <= {data_addr[6:0],sync_data};
                    if(addr_bit_count== 3'b1 && data_addr[0]==1'b0) begin
                        current_state <= state_error;
                    end else if(addr_bit_count==3'd7) begin
                        
                        if({data_addr[5:0],sync_data}>MAX_ADDRESS) begin
                            current_state <= state_error;
                        end else begin
                            current_state <= state_sample_data;
                        end
                    end else begin
                        
                        addr_bit_count <= addr_bit_count + 3'd1;
                    end
                end
            end
            state_sample_data: begin
                if(sclk_rising_edge) begin
                    data_out <= {data_out[6:0],sync_data};
                    if(data_bit_count==3'd7) begin
                        current_state<=state_idle;
                        transaction_ready<=1'b1;
                    end else begin
                        data_bit_count <= data_bit_count + 3'd1;
                    end
                end
            end
            state_error: begin
            end
            default:current_state<=state_idle;
        endcase
    end




end
    
    






endmodule