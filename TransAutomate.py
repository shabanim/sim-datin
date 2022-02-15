from collections import defaultdict
import matplotlib.pyplot as plt
import math

class TransformerAutomation:
    def __init__(self,seq,hd,nl,ci):
        self.peak_tp = [205,254,288,309,321,327,330]
        self.seq = seq
        self.hd = hd
        self.nl = nl
        self.ci = ci
        self.params = 12*nl*(hd**2)
        self.k = 16
        self.b_2_GB = 1024*1024*1024

    def find_efficiency(self,ait,bw,bsz):
        return (ait*(bw/1000))/((ait*(bw/1000))+self.peak_tp[int(bsz)])

    def find_AIT(self,bsz,component):
        if(component == "parameter_gradient"):
            return self.seq*bsz
        elif(component == "optimizer_state"):
            return self.seq*(bsz/4)
        elif(component == "activation_checkpoint"):
            return 24*self.hd*self.ci
    
    def find_memory_footprint(self,component=None):
        if(component is None):
            return ((2+2+self.k)*self.params)*self.b_2_GB
        elif(component=="weight_size" or component=="weight_grad_size"):
            return (self.params*2)*self.b_2_GB
        elif(component=="optimizer_size"):
            return (self.params*self.k)*self.b_2_GB

    def sweep_bw(self,bsz,start,end,step):
        efficiency = defaultdict(lambda:[])
        AITcomponent = ["parameter_gradient","optimizer_state","activation_checkpoint"]
        for bw in range(start,end,step):
            for component in AITcomponent:
                ait = self.find_AIT(bsz,component)
                efficiency[component].append(self.find_efficiency(ait,bw,math.log(bsz,2)))
        return efficiency
    
    def sweep_bsz(self,bsz_start,bsz_end,bsz_step,bw_start,bw_end,bw_step):
        colors = ['b','g','r','c','m','y','k','w']
        c = 0
        FinalEfficiency=[]
        for bsz in range(bsz_start,bsz_end,bsz_step):
            FinalEfficiency.append(self.sweep_bw(2**bsz,bw_start,bw_end,bw_step))
        
        fig, ax = plt.subplots(1,3,figsize=(5,5))
        for i,component in enumerate(FinalEfficiency[0].keys()):
            ax[i].set_title(f"{component} Bandwidth")
            c = 0
            for bsz in range(bsz_start,bsz_end,bsz_step):
                x = list(range(bw_start,bw_end,bw_step))
                y = FinalEfficiency[bsz-1][component]
                ax[i].plot(x,y,label = f"B-{2**bsz}",color = colors[c])
                c+=1
            ax[i].legend()

        for axs in ax.flat:
            axs.set(xlabel='Bandwidth (GB/s)', ylabel='Efficiency')
        for axs in ax.flat:
            axs.label_outer()
        plt.show()

if __name__ == "__main__":
    TA = TransformerAutomation(seq=1024,hd=25600,nl=128,ci=1)
    TA.sweep_bsz(bsz_start=0,bsz_end=7,bsz_step=1,bw_start=1,bw_end=300,bw_step=50)