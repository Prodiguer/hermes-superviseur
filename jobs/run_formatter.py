
# Imports.
import argparse
import os
import uuid

import hermes
import superviseur
from hermes.db import pgres as db
from hermes.utils import logger



# Define command line arguments.
_ARGS = argparse.ArgumentParser("Writes a formatted superviseur script to file system.")
_ARGS.add_argument(
    "-j", "--job",
    help="Unique identifier of a job that failed or was late",
    dest="job_uid",
    type=str
    )


# Output directory is derived from script location.
_OUT_DIR = os.path.dirname(__file__)


def _get_data(job_uid):
    """Returns required data from database.

    """
    with db.session.create():
        job = db.dao_monitoring.retrieve_job(job_uid)
        if job is None:
            raise ValueError("Job does not exist in database")

        job_periods = db.dao_monitoring.retrieve_latest_job_periods(job_uid)
        if not job_periods:
            raise ValueError("Job period does not exist in database")

        simulation = db.dao_monitoring.retrieve_simulation(job.simulation_uid)
        if simulation is None:
            raise ValueError("Simulation does not exist in database")

        #supervision = db.dao_superviseur.retrieve_supervision(1)
        #if supervision is None:
        #    raise ValueError("Supervision does not exist in database")

        user = superviseur.authorize(simulation.compute_node_login)
        if user is None:
            raise ValueError("User does not exist in database")

        return simulation, job, job_periods[-1], None, user


def _write_script(script, job):
    """Writes script to file system.

    """
    fname = "run-formatter-{}.sh".format(job.job_uid)
    fpath = os.path.join(_OUT_DIR, fname)
    with open(fpath, 'wb') as output_file:
        output_file.write(script)
    logger.log("Superviseur script written to --> {}".format(fpath))


def _execute_formatter(simulation, job, supervision, user):
    """Executes the superviseur formatter function.

    """
    params = superviseur.FormatParameters(
        simulation,
        job,
        supervision,
        user
        )
    try:
        script = superviseur.format_script(params)
    except Exception as err:
        logger.log_error(err)
    else:
        #print script
        _write_script(script, job)


def _main(args):
    """Main entry point.

    """
    # Validate input arguments.
    try:
        uuid.UUID(args.job_uid)
    except ValueError:
        raise ValueError("Job identifier is invalid")

    # Load data from database.
    simulation, job, job_period, supervision, user = \
        _get_data(args.job_uid)

    # Dispatch script to HPC for execution.
    _execute_formatter(simulation, job, supervision, user)



# Main entry point.
if __name__ == '__main__':
    _main(_ARGS.parse_args())
