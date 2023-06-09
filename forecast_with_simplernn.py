

from google.colab import files
 
data_file = files.upload()

import pandas as pd
import numpy as np


import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.layers import Dense, Dropout, Activation, Flatten, Input, Dense, concatenate
from tensorflow.keras.layers import LSTM, SimpleRNN, Conv1D, Bidirectional
from tensorflow.keras.models import Sequential, clone_model, Model
from tensorflow.keras.optimizers import RMSprop, Adam
from tensorflow.keras import regularizers, metrics, callbacks
from tensorflow.keras.callbacks import TensorBoard
from keras import layers
from sklearn.preprocessing import StandardScaler

import matplotlib.pyplot as plt
import time
import datetime, os

# Commented out IPython magic to ensure Python compatibility.
# %load_ext tensorboard

data_df = pd.read_csv('data.csv',index_col = 0)

data_df.set_index(pd.DatetimeIndex(data_df.index), inplace=True)

data_df = data_df.drop('returns', axis=1)
# shift mid price by 1
shifted_df= data_df.shift()
# merge mid and Shifter mid values
concat_df = [data_df, shifted_df[['mid']]]
data = pd.concat(concat_df,axis=1)
# Replace NaNs with 0
data.fillna(0, inplace=True)
data.columns = [*data.columns[:-1], 'y']
data.head()

plt.plot(data.index, data.mid)

def show_heatmap(data):
    plt.matshow(data.corr())
    plt.xticks(range(data.shape[1]), data.columns, fontsize=8, rotation=90)
    plt.gca().xaxis.tick_bottom()
    plt.yticks(range(data.shape[1]), data.columns, fontsize=8)

    cb = plt.colorbar()
    cb.ax.tick_params(labelsize=8)
    plt.title("Feature Correlation Heatmap", fontsize=8)
    plt.show()


show_heatmap(data.loc[:, ~data.columns.isin(['y'])])

# unselecting redundant columns with high corelation among each other, e.g. (b1 & b3), (b6 & b9 & b15), (b7 & b15) so taking out extra
selected_features = [x for x in data.columns if x not in ['b3','b6','b7','b9']]
selected_data = data[selected_features]

# Variables
n_points, n_features = selected_data.shape
print(n_points, n_features)
n_timestamps = 1
batch_size = 32
epochs=20
val_perct = 0.1
test_perct = 0.1
seed = 42

def get_dataset(data, val_perct = 0.1, test_perct = 0.1, batch_size = 32, n_timestamps = 1):

    num_val_samples = int(data.shape[0]*val_perct)
    num_test_samples = int(data.shape[0]*test_perct)
    num_train_samples = data.shape[0] - num_val_samples - num_test_samples
    train_data = data.iloc[0 : num_train_samples]
    val_data = data.iloc[num_train_samples: num_train_samples+num_val_samples]
    test_data = data.iloc[num_train_samples+num_val_samples:]

    # Normalize the data
    scaler = StandardScaler()
    scaled_train_data = scaler.fit_transform(train_data)
    scaled_val_data = scaler.transform(val_data)
    scaled_test_data = scaler.transform(test_data)

    # split features and target
    x_train = np.expand_dims(scaled_train_data[:,:-1].astype("float32"), n_timestamps)
    y_train = scaled_train_data[:,-1].astype("float32")

    x_val = np.expand_dims(scaled_val_data[:,:-1].astype("float32"), n_timestamps)
    y_val = scaled_val_data[:,-1].astype("float32")

    x_test = np.expand_dims(scaled_test_data[:,:-1].astype("float32"), n_timestamps)
    y_test = scaled_test_data[:,-1].astype("float32")

    return (
        tf.data.Dataset.from_tensor_slices((x_train, y_train)).batch(batch_size),
        tf.data.Dataset.from_tensor_slices((x_val, y_val)).batch(batch_size),
        tf.data.Dataset.from_tensor_slices((x_test, y_test)).batch(batch_size),
    )

train_dataset, val_dataset, test_dataset = get_dataset(selected_data, val_perct = val_perct, test_perct = test_perct, batch_size = batch_size, n_timestamps = n_timestamps)

def get_compiled_model(optim_type, dense_layer, num_unit):
  
  model = Sequential()
  model.add(SimpleRNN(units=num_unit, input_shape=(1,n_features-1), activation="relu"))

  for _ in range(dense_layer):
      model.add(Dense(units=num_unit, activation='relu'))

  model.add(Dense(units=1, activation='linear'))

  model.compile(loss='mae', optimizer=optim_type) 

  return model

!rm -rf ./logs/

tf.random.set_seed(seed)

optim_types = ['adam', 'rmsprop']
dense_layers = [1,2]
num_units = [256, 512]

path_checkpoint = "model1_checkpoint.h5"
modelckpt_callback = callbacks.ModelCheckpoint(monitor="val_loss", filepath=path_checkpoint, verbose=1, save_weights_only=False, save_best_only=True)
earlystopping = callbacks.EarlyStopping(monitor ="val_loss", mode ="min", patience = 5)

for optim_type in optim_types:
    for dense_layer in dense_layers:
      for num_unit in num_units:
        name = "{}-{}-units-{}-dense-".format(optim_type, num_unit, dense_layer)
        logdir = os.path.join("logs", name, datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
        tensorboard_callback = tf.keras.callbacks.TensorBoard(logdir, histogram_freq=1)
        
        model = get_compiled_model(optim_type, dense_layer, num_unit)

        model.fit(train_dataset, batch_size=batch_size, epochs=epochs, verbose=1, validation_data=val_dataset, callbacks=[tensorboard_callback, earlystopping, modelckpt_callback])

model = keras.models.load_model(path_checkpoint)
model.evaluate(test_dataset)

# Commented out IPython magic to ensure Python compatibility.
# %tensorboard --logdir logs

"""From the above, best model is SimpleRNN-rmsprop-256-units-1-dense"""

