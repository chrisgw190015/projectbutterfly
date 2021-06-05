# -*- coding: utf-8 -*-
"""
Created on 15 March 2021

@author: Wong Wai Cheng

Description: This file contains the workflow of building different image classifiers with MobileNets.
Aim: Build a classifier for classifying species of butterflies via transfer learning (base model as feature extractor only).
"""

# Import libraries and custom functions from function.py
from functions import prep_data, features_mobile1, features_mobile2, \
    features_aug_mobile1, features_aug_mobile2, \
    plot_confusion_matrix, plot_result
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tensorflow as tf
from joblib import dump
from joblib import load
from keras import models
from keras import layers
from keras import optimizers
from sklearn.svm import LinearSVC
from sklearn.model_selection import KFold
from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report
from keras.layers import Dropout

"""
Split data to train and test - Malaysia dataset
"""
# Declare folder names in bug dictionary. Set number of files to copy to train and test sets.
for bug in ['catopsilia-pomona', 'danaus-chrysippus', 'eurema-hecabe', 'graphium-doson',
            'graphium-sarpedon', 'junonia-hedonia', 'junonia-iphita', 'papilio-demoleus']:
    print(bug)
    prep_data(directory='/Users/chris/Desktop/MasterofDataScience/thesis_related/dataset/final/',
              species=bug,
              train_size=700,
              test_size=194)

# Set directories
train_path = '/Users/chris/Desktop/MasterofDataScience/thesis_related/dataset/final/train'
test_path = '/Users/chris/Desktop/MasterofDataScience/thesis_related/dataset/final/test-all'

train_size = 5600 # number of images in the train folder; doubled after augmentation
test_size = 1552  # number of images in the test folder

"""
MobileNets Training Set-up:
1. Feature and label extraction
2. Summary - classification report and confusion matrix
"""
from datetime import datetime
start = datetime.now()
# Extract features without augmentation
train_features, train_labels = features_mobile1b(train_path, train_size, 224, 224, 7, 8)
test_features, test_labels = features_mobile1b(test_path, test_size, 224, 224, 7, 8)

# assert train_features.shape == (4800,7,7,1024)
# assert train_labels.shape == (4800,8)

# Extract features with augmentation
train_features_aug, train_labels_aug = features_aug_mobile2(train_path, train_size, 224, 224, 7, 8)

duration = datetime.now() - start
print("Training completed in time: ", duration)

# Combine extracted features
train_features_combined = np.concatenate((train_features, train_features_aug))
train_labels_combined = np.concatenate((train_labels, train_labels_aug))

"""
MobileNets + 10 KFold + Flatten + Softmax
"""
epochs = 15
batch_size = 32
num_folds = 10
kfold = KFold(n_splits=num_folds, shuffle=True)

acc_per_fold = []
loss_per_fold = []
precision_per_fold = []
recall_per_fold = []

# set up loop for 10 kfold cross validation
fold_no = 1
# build layers
from datetime import datetime
start = datetime.now()

for train, test in kfold.split(train_features, train_labels):
    mobile_soft_flat = models.Sequential()
    mobile_soft_flat.add(layers.Flatten(input_shape = (7,7,1024)))
    mobile_soft_flat.add(Dropout(0.5))
    mobile_soft_flat.add(layers.Dense(8, activation = 'softmax'))
    mobile_soft_flat.summary()
    # compile model
    mobile_soft_flat.compile(optimizer = optimizers.RMSprop(lr=0.0001),
                          loss = 'categorical_crossentropy',
                          metrics = ['accuracy', tf.keras.metrics.Precision(),
                                     tf.keras.metrics.Recall()])

    print('------------------------------------------------------------------------')
    print(f'Training for fold {fold_no} ...')
    # run model training
    history_mobile_flat = mobile_soft_flat.fit(train_features[train], train_labels[train],
                                epochs = epochs,
                                batch_size = batch_size, steps_per_epoch=11200/32)
    # print scores for each fold
    scores = mobile_soft_flat.evaluate(train_features[test], train_labels[test], verbose = 0)
    print(f'Score for fold {fold_no}: {mobile_soft_flat.metrics_names[0]} of {scores[0]}; {mobile_soft_flat.metrics_names[1]} of {scores[1]*100}%')
    acc_per_fold.append(scores[1])
    loss_per_fold.append(scores[0])
    precision_per_fold.append(scores[2])
    recall_per_fold.append(scores[3])

    plot_result(history_mobile_flat)

    fold_no = fold_no + 1
duration = datetime.now() - start
print("Training completed in time: ", duration)

# print score for each fold and average with s.d.
print('------------------------------------------------------------------------')
print('Score per fold')
for i in range(0, len(acc_per_fold)):
  print('------------------------------------------------------------------------')
  print(f'> Fold {i+1} - Loss: {loss_per_fold[i]} - Accuracy: {acc_per_fold[i]} - Precision: {precision_per_fold[i]} - Recall: {recall_per_fold[i]}%')
print('------------------------------------------------------------------------')
print('Average scores for all folds:')
print(f'> Accuracy: {np.mean(acc_per_fold)} \u00B1 {np.std(acc_per_fold)}')
print(f'> Loss: {np.mean(loss_per_fold)} \u00B1 {np.std(loss_per_fold)}')
print(f'> Precision: {np.mean(precision_per_fold)} \u00B1 {np.std(precision_per_fold)}')
print(f'> Recall: {np.mean(recall_per_fold)} \u00B1 {np.std(recall_per_fold)}')
print('------------------------------------------------------------------------')

# save trained model for predicting test set later
mobile_soft_flat.save('10mobilev2_softflat_aug.h5')
mobile_soft_flat.save('10mobilev2_softflat_aug.h5')

# MobileNets-Flatten: Evaluate using test set
y_actual = np.argmax(test_labels, axis = 1)
labels = ['catopsilia-pomona', 'danaus-chrysippus', 'eurema-hecabe', 'graphium-doson',
            'graphium-sarpedon', 'junonia-hedonia', 'junonia-iphita', 'papilio-demoleus']

mobile_soft_flat = tf.keras.models.load_model('10mobilev2_softflat_aug.h5')
score = mobile_soft_flat.evaluate(test_features, test_labels)
print("%s: %.2f%%" % (mobile_soft_flat.metrics_names[1], score[1]*100))
y_pred = mobile_soft_flat.predict(test_features)
y_pred_argmax = np.argmax(y_pred, axis = 1)
confusion_matrix(y_actual, y_pred_argmax)
cm_mobile_flat = tf.math.confusion_matrix(labels = y_actual, predictions = y_pred_argmax).numpy()
cm_mobile_flat_df = pd.DataFrame(cm_mobile_flat,
                               index = labels,
                               columns = labels)

print(classification_report(y_actual, y_pred_argmax, digits = 4))

plot_confusion_matrix(cm=cm_mobile_flat, classes=labels, title='MobileNetV2-Flatten-Softmax')
plt.tight_layout()
plt.savefig('10mobilev2_softflat_aug.png')
plt.clf()

"""
LEEDS Dataset
"""
# Set directories
train_path = '/Users/chris/Downloads/leedsbutterfly/leeds-train-cv'
test_path = '/Users/chris/Downloads/leedsbutterfly/leeds-test'

train_size = 742 # number of images in the train folder; doubled after augmentation
test_size = 90

# Extract features without augmentation
from datetime import datetime
start = datetime.now()

train_features, train_labels = features_mobile2(train_path, train_size, 224, 224, 7, 10)
test_features, test_labels = features_mobile2(test_path, test_size, 224, 224, 7, 10)

# Extract features with augmentation
train_features_aug, train_labels_aug = features_aug_mobile2(train_path, train_size, 224, 224, 7, 10)

duration = datetime.now() - start
print("Feature extraction completed in time: ", duration)

# Combine extracted features
train_features_combined = np.concatenate((train_features, train_features_aug))
train_labels_combined = np.concatenate((train_labels, train_labels_aug))

epochs = 10
batch_size = 32
num_folds = 10

acc_per_fold = []
loss_per_fold = []
precision_per_fold = []
recall_per_fold = []

kfold = KFold(n_splits=num_folds, shuffle=True)

fold_no = 1
# build layers
from datetime import datetime
start = datetime.now()

for train, test in kfold.split(train_features_combined, train_labels_combined):
    model = models.Sequential()
    model.add(layers.Flatten(input_shape=(7, 7, 1280)))
    model.add(Dropout(0.5))
    model.add(layers.Dense(10, activation='softmax'))
    model.summary()
    # compile model
    model.compile(optimizer=optimizers.RMSprop(lr=0.0001),
                  loss='categorical_crossentropy',
                  metrics=['accuracy', tf.keras.metrics.Precision(),
                           tf.keras.metrics.Recall()])

    print('------------------------------------------------------------------------')
    print(f'Training for fold {fold_no} ...')
    # run model training
    history_mobile = model.fit(train_features_combined[train], train_labels_combined[train],
                              epochs=epochs,
                              batch_size=batch_size, steps_per_epoch=1484/32)
    # print scores for each fold
    scores = model.evaluate(train_features_combined[test], train_labels_combined[test], verbose=0)
    print(
        f'Score for fold {fold_no}: {model.metrics_names[0]} of {scores[0]}; {model.metrics_names[1]} of {scores[1]}%')
    acc_per_fold.append(scores[1])
    loss_per_fold.append(scores[0])
    precision_per_fold.append(scores[2])
    recall_per_fold.append(scores[3])

    plot_result(history_mobile)

    fold_no = fold_no + 1
duration = datetime.now() - start
print("Training completed in time: ", duration)

# print score for each fold and average with s.d.
print('------------------------------------------------------------------------')
print('Score per fold')
for i in range(0, len(acc_per_fold)):
  print('------------------------------------------------------------------------')
  print(f'> Fold {i+1} - Loss: {loss_per_fold[i]} - Accuracy: {acc_per_fold[i]} - Precision: {precision_per_fold[i]} - Recall: {recall_per_fold[i]}%')
print('------------------------------------------------------------------------')
print('Average scores for all folds:')
print(f'> Accuracy: {np.mean(acc_per_fold)} \u00B1 {np.std(acc_per_fold)}')
print(f'> Loss: {np.mean(loss_per_fold)} \u00B1 {np.std(loss_per_fold)}')
print(f'> Precision: {np.mean(precision_per_fold)} \u00B1 {np.std(precision_per_fold)}')
print(f'> Recall: {np.mean(recall_per_fold)} \u00B1 {np.std(recall_per_fold)}')
print('------------------------------------------------------------------------')

model.save('mobilev2_aug_leeds.h5')

# Test set
y_actual = np.argmax(test_labels, axis = 1)
labels = ['d plexippus', 'h charitonius', 'h erato', 'j coenia', 'l phlaeas',
          'n antiopa', 'p cresphontes', 'p rapae', 'v atalanta', 'v cardui']

model = tf.keras.models.load_model('mobilev2_aug_leeds.h5')
score = model.evaluate(test_features, test_labels)
print("%s: %.2f%%" % (model.metrics_names[1], score[1]*100))
y_pred = model.predict(test_features)
y_pred_argmax = np.argmax(y_pred, axis = 1)
confusion_matrix(y_actual, y_pred_argmax)
cm_model = tf.math.confusion_matrix(labels = y_actual, predictions = y_pred_argmax).numpy()
cm_model_df = pd.DataFrame(cm_model,
                               index = labels,
                               columns = labels)

print(classification_report(y_actual, y_pred_argmax, digits = 4))

plot_confusion_matrix(cm=cm_model, classes=labels, title='MobileNetV2-Aug-LEEDS')
plt.tight_layout()
plt.savefig('mobilev2_aug_leeds.png')
plt.clf()

###############################################################################################
                                        #End#
###############################################################################################