
import numpy as np
import time
from openvino.inference_engine import IENetwork, IECore
import os
import cv2
import argparse
import sys

# Only in case if COCO models where used:
# LABELS_COCO = ["background","person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"]

class Queue:
    '''
    Class for dealing with queues
    '''
    def __init__(self):
        self.queues = []

    def add_queue(self, points):
        self.queues.append(points)

    def get_queues(self, image):
        for q in self.queues:
            x_min, y_min, x_max, y_max=q
            frame = image[y_min:y_max, x_min:x_max]
            yield frame
    
    def check_coords(self, coords):
        d = {k+1:0 for k in range(len(self.queues))}
        for coord in coords:
            for i, q in enumerate(self.queues):
                if coord[0] > q[0] and coord[2] < q[2]:
                    d[i+1] += 1
        return d

class PersonDetect:
    '''
    Class for the Person Detection Model.
    '''
    def __init__(self, model_name, device, threshold=0.60):
        self.model_weights      = (model_name + '.bin')
        self.model_structure    = (model_name + '.xml')
        self.device             = device
        self.threshold          = threshold

        try:
            self.model          = IENetwork(self.model_structure, self.model_weights)
            #self.model = IECore.read_network(self.model_structure, self.model_weights) # Use this sentence with OpenVino V2020.##.
        except Exception as e:
            raise ValueError("Could not Initialise the network. Have you enterred the correct model path?")

        self.input_name     = next(iter(self.model.inputs))
        self.input_shape    = self.model.inputs[self.input_name].shape
        self.output_name    = next(iter(self.model.outputs))
        self.output_shape   = self.model.outputs[self.output_name].shape

    def load_model(self):
        '''
        TODO: This method needs to be completed by you
        '''
        self.core   = IECore()
        self.net    = self.core.load_network(network=self.model, device_name=args.device, num_requests=0)
        
        return
        
    def predict(self, image):
        '''
        TODO: This method needs to be completed by you
        '''
        self.processed_image    = self.preprocess_input(image)
        results                 = self.net.infer(inputs = {self.input_name: self.processed_image})
        output_networks         = results[self.output_name]
        self.coords, self.image = self.draw_outputs(output_networks, image)
        self.image              = self.preprocess_outputs(self.image)

        return self.coords, self.image 

    def draw_outputs(self, output_networks, image):
        '''
        TODO: This method needs to be completed by you
        '''
        ### Rectangle graphical configuration.
        rec_color       = (0, 255, 0) # Green rectangle in BGR.
        rec_thickness   = 1
        rec_linetype    = cv2.LINE_AA
        # Configure inference time text configuration:
#        inf_time_msg    = ''
#        font            = cv2.FONT_HERSHEY_SIMPLEX 
#        org             = (5, 15) 
#        fontScale       = 0.5
#        color           = (0, 0, 255) # Red color in BGR.
#        thickness       = 1
        ### Set other variables:
        coords          = []

        for box in output_networks[0][0]:
            conf = box[2]
            if conf >= self.threshold:
                xmin = int(box[3] * image.shape[1])
                ymin = int(box[4] * image.shape[0])
                xmax = int(box[5] * image.shape[1])
                ymax = int(box[6] * image.shape[0])
                cv2.rectangle(image, (xmin, ymin), (xmax, ymax), rec_color, rec_thickness, rec_linetype)
                coords.append((xmin, ymin, xmax, ymax))

#                if args.coco == True:
#                    # Draw detection label:
#                    class_idx       = int(box[1])
#                    xmin_pos_text   = (xmin + 5)
#                    ymax_pos_text   = (ymax - 5)
#                    if 0 <= class_idx < len(LABELS_COCO):
#                        class_name = LABELS_COCO[class_idx]
#                    else:
#                        class_name = ''
#                        conf_percent = (conf * 100)
#                    cv2.putText(image, "{} {:.2%}".format(class_name, conf), (xmin_pos_text, ymax_pos_text), font, fontScale, rec_color, thickness, cv2.LINE_AA)

        return coords, image

    def preprocess_outputs(self, outputs):
        '''
        TODO: This method needs to be completed by you
        '''
        self.output = cv2.resize(outputs, (self.output_shape[3], self.output_shape[2]))

        return self.output


    def preprocess_input(self, image):
        '''
        TODO: This method needs to be completed by you
        '''
        self.image = cv2.resize(image, (self.input_shape[3], self.input_shape[2]))
        self.image = self.image.transpose((2, 0, 1))  
        self.image = self.image.reshape(1, *self.image.shape)

        return self.image

def main(args):
    model       = args.model
    device      = args.device
    video_file  = args.video
    max_people  = args.max_people
    threshold   = args.threshold
    output_path = args.output_path

    start_model_load_time = time.time()
    pd = PersonDetect(model, device, threshold)
    pd.load_model()
    total_model_load_time = (time.time() - start_model_load_time)

    queue = Queue()
    
    try:
        queue_param = np.load(args.queue_param)
        for q in queue_param:
            queue.add_queue(q)
    except:
        print("Error loading queue param file.")

    try:
        cap = cv2.VideoCapture(video_file)
    except FileNotFoundError:
        print("Cannot locate video file: "+ video_file)
    except Exception as e:
        print("Something else went wrong with the video file: ", e)
    
    initial_w               = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    initial_h               = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video_len               = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps                     = int(cap.get(cv2.CAP_PROP_FPS))
    out_video               = cv2.VideoWriter(os.path.join(output_path, 'output_video.mp4'), cv2.VideoWriter_fourcc(*'avc1'), fps, (initial_w, initial_h), True)
    #out_video               = cv2.VideoWriter(os.path.join(output_path, 'output_video.mp4'), 0x00000021, fps, (initial_w, initial_h), True) # Only for check purposes.
    print("Video was wrote!!!!") # Only to check if the video was wrote.
    counter                 = 0
    start_inference_time    = time.time()

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            counter += 1
            
            coords, image   = pd.predict(frame)
            num_people      = queue.check_coords(coords)
            print(f"Total People in frame = {len(coords)}")
            print(f"Number of people in queue = {num_people}")
            out_text        = ""
            y_pixel         = 25
            
            for k, v in num_people.items():
                out_text += f"No. of People in Queue {k} is {v} "
                if v >= int(max_people):
                    out_text += f" Queue full; Please move to next Queue "
                cv2.putText(image, out_text, (15, y_pixel), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)
                out_text = ""
                y_pixel += 40
            out_video.write(image)
            
        total_time              = time.time()-start_inference_time
        total_inference_time    = round(total_time, 1)
        fps                     = (counter/total_inference_time)

        with open(os.path.join(output_path, 'stats.txt'), 'w') as f:
            f.write(str(total_inference_time)+'\n')
            f.write(str(fps)+'\n')
            f.write(str(total_model_load_time)+'\n')

        cap.release()
        cv2.destroyAllWindows()
    except Exception as e:
        print("Could not run Inference: ", e)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--device', default='CPU')
    parser.add_argument('--video', default=None)
    parser.add_argument('--queue_param', default=None)
    parser.add_argument('--output_path', default='/results')
    parser.add_argument('--max_people', default=2)
    parser.add_argument('--threshold', default=0.60)
    #parser.add_argument('--coco', default=False) # Only in case of using COCO models.
    
    args = parser.parse_args()

    main(args)