from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, flash
from functools import wraps
from flask_bcrypt import Bcrypt
import os
from datetime import datetime
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from enum import Enum
from models import User, UserRole,  UserStatus, Gender
from app import db